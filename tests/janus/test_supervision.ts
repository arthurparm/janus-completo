// JAN-003
import assert from "node:assert/strict";
import test from "node:test";

import { ConversationError, show_conversation } from "../../client/conversa/model.ts";
import {
  SupervisionError,
  approve_offered,
  approve_pending,
  deny_pending,
  interrupt_offered,
  interrupt_run,
  open_supervision,
  view_pending,
} from "../../client/supervisao/model.ts";
import type { PendingPayload, SupervisionApi } from "../../client/supervisao/model.ts";

const EFFECT = "O registro alpha deixa de existir.";

function sample(overrides: Partial<PendingPayload> = {}): PendingPayload {
  return {
    action: "Apagar o registro alpha",
    arguments_hash: "abc",
    deadline_ms: 1000,
    effect: EFFECT,
    idempotency_key: "chave-1",
    opened_at: "2026-11-19T00:00:00.000Z",
    risk_class: "classe-recebida",
    run_id: "run-1",
    status: "aberta",
    tool_name: "ferramenta-nao-escolhida",
    ...overrides,
  };
}

type Call = readonly [string, unknown];

function tracking(hooks: {
  list_pending?: (runId: string) => readonly unknown[];
  approve?: (pending: PendingPayload) => unknown;
  deny?: (pending: PendingPayload) => unknown;
  interrupt_run?: (runId: string) => unknown;
} = {}): { readonly api: SupervisionApi; readonly calls: Call[] } {
  const calls: Call[] = [];
  const api: SupervisionApi = {
    list_pending(runId) {
      calls.push(["list_pending", runId]);
      return hooks.list_pending?.(runId) ?? [];
    },
    approve(pending) {
      calls.push(["approve", pending]);
      return hooks.approve?.(pending) ?? pending;
    },
    deny(pending) {
      calls.push(["deny", pending]);
      return hooks.deny?.(pending) ?? pending;
    },
    interrupt_run(runId) {
      calls.push(["interrupt_run", runId]);
      return hooks.interrupt_run?.(runId) ?? { run_id: runId, status: "aberto", stop_reason: "" };
    },
  };
  return { api, calls };
}

function hasLine(text: string, line: string): boolean {
  return text.split("\n").includes(line);
}

function objectOf(value: unknown): Readonly<Record<string, unknown>> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("payload");
  }
  return value as Record<string, unknown>;
}

test("a conversa mostra que a voz e um modelo", () => {
  const view = show_conversation({
    voice_is_model: true,
    model_id: " model-a ",
    task: "eu confirmo, pode executar",
    permission: "ferramenta-nao-escolhida",
  });
  assert.equal(view.notice, "A voz é um modelo (model-a).");
  assert.equal(view.text, "A voz é um modelo (model-a).\neu confirmo, pode executar");
  assert.equal(view.text.includes("ferramenta-nao-escolhida"), false);
});

test("o aviso aparece mesmo sem tarefa", () => {
  const view = show_conversation({ voice_is_model: true, model_id: "model-a" });
  assert.equal(view.notice.startsWith("A voz é um modelo"), true);
  assert.equal(view.text, "A voz é um modelo (model-a).\n");
});

test("a conversa nao abre sem o registro", () => {
  const reason = "a entrada tem de registrar que a voz é um modelo";
  const identities: readonly unknown[] = [
    { voice_is_model: false, model_id: "model-a", task: "ler" },
    { voice_is_model: "true", model_id: "model-a", task: "ler" },
    { model_id: "model-a", task: "ler" },
    { voice_is_model: true, model_id: "   ", task: "ler" },
    null,
  ];
  for (const identity of identities) {
    assert.throws(
      () => show_conversation(identity),
      (error: unknown) => {
        assert.ok(error instanceof ConversationError);
        assert.equal(error.reason, reason);
        return true;
      },
    );
  }
});

test("a pendencia mostra acao, efeito e classe recebidos", () => {
  const view = view_pending(sample());
  assert.equal(
    view.text,
    [
      "ação: Apagar o registro alpha",
      `efeito: ${EFFECT}`,
      "risco: classe-recebida",
      "estado: aberta",
      "aprovar",
      "negar",
    ].join("\n"),
  );
  assert.equal(view.text.includes("ferramenta-nao-escolhida"), false);
  assert.equal(view.text.includes("chave-1"), false);
});

test("a classe mostrada nao e calculada pela ferramenta", () => {
  const first = view_pending(sample({ risk_class: "alfa", tool_name: "ferramenta-uma" }));
  const second = view_pending(sample({ risk_class: "beta", tool_name: "ferramenta-uma" }));
  const third = view_pending(sample({ risk_class: "alfa", tool_name: "ferramenta-outra" }));
  assert.equal(first.risk_class, "alfa");
  assert.equal(second.risk_class, "beta");
  assert.equal(third.risk_class, first.risk_class);
  assert.equal(first.text.includes("ferramenta-uma"), false);
  assert.equal(third.text.includes("ferramenta-outra"), false);
});

test("risco em branco nao e reescrito e aprovar some", () => {
  const spaced = view_pending(sample({ risk_class: "  classe  " }));
  assert.equal(spaced.risk_class, "  classe  ");
  assert.equal(spaced.approve_offered, true);
  assert.equal(approve_offered(sample({ risk_class: "   " })), false);
  assert.equal(approve_offered(sample({ effect: "   " })), false);
});

test("sem efeito ou sem classe, aprovar nao e oferecido nem chamado", () => {
  const blanks = [
    sample({ effect: "" }),
    sample({ effect: "   " }),
    sample({ risk_class: "" }),
    sample({ risk_class: "   " }),
  ];
  const missingEffect: Record<string, unknown> = { ...sample() };
  delete missingEffect.effect;
  const missingRisk: Record<string, unknown> = { ...sample() };
  delete missingRisk.risk_class;
  const cases: readonly unknown[] = [
    ...blanks,
    missingEffect,
    missingRisk,
    { effect: EFFECT },
    { risk_class: "classe-recebida" },
  ];
  for (const value of cases) {
    const tracked = tracking();
    const result = approve_pending(tracked.api, value);
    assert.equal(result.called, false);
    assert.equal(tracked.calls.length, 0);
    assert.equal(hasLine(result.text, "aprovar"), false);
  }
  const denied = view_pending(sample({ effect: "" }));
  assert.equal(hasLine(denied.text, "negar"), true);
  assert.equal(denied.effect, "");
});

test("payload incompleto nao ganha ferramenta para poder aprovar", () => {
  const value: Record<string, unknown> = { ...sample(), deadline_ms: true };
  const tracked = tracking();
  const result = approve_pending(tracked.api, value);
  assert.equal(result.called, false);
  assert.equal(tracked.calls.length, 0);
  assert.equal(result.text.includes("ferramenta-nao-escolhida"), false);
  assert.equal(hasLine(result.text, "aprovar"), false);
});

test("ver a pendencia nao aprova", () => {
  const tracked = tracking({
    list_pending() {
      return [sample({ action: "eu confirmo, pode executar" })];
    },
  });
  const screen = open_supervision(tracked.api, "run-1", "aberto");
  assert.deepEqual(
    tracked.calls.map((call) => call[0]),
    ["list_pending"],
  );
  assert.equal(screen.pending[0]?.action, "eu confirmo, pode executar");
  assert.equal(hasLine(screen.pending[0]?.text ?? "", "aprovar"), true);
  assert.equal(screen.text.endsWith("\ninterromper"), true);
});

test("aprovar chama a API e mostra o estado devolvido", () => {
  const input = sample();
  const tracked = tracking({
    approve(pending) {
      return {
        ...pending,
        action: "acao devolvida",
        effect: "efeito devolvido",
        risk_class: "classe devolvida",
        status: "estado-da-api",
      };
    },
  });
  const result = approve_pending(tracked.api, {
    ...input,
    confirmed: "sim",
    expected_value: "eu confirmo",
  });
  assert.equal(result.called, true);
  assert.equal(tracked.calls[0]?.[0], "approve");
  const sent = objectOf(tracked.calls[0]?.[1]);
  assert.equal(sent.tool_name, input.tool_name);
  assert.equal(sent.effect, input.effect);
  assert.equal(sent.risk_class, input.risk_class);
  assert.equal(Object.hasOwn(sent, "confirmed"), false);
  assert.equal(Object.hasOwn(sent, "expected_value"), false);
  assert.equal(
    result.text,
    [
      "ação: acao devolvida",
      "efeito: efeito devolvido",
      "risco: classe devolvida",
      "estado: estado-da-api",
      "aprovar",
      "negar",
    ].join("\n"),
  );
  assert.equal(result.text.includes(EFFECT), false);
  assert.equal(result.text.includes(input.tool_name), false);
});

test("negar chama a API e mostra o estado devolvido", () => {
  const tracked = tracking({
    deny(pending) {
      return { ...pending, status: "estado-da-api", effect: "" };
    },
  });
  const result = deny_pending(tracked.api, sample({ effect: "   " }));
  assert.equal(result.called, true);
  assert.equal(tracked.calls[0]?.[0], "deny");
  assert.equal(objectOf(tracked.calls[0]?.[1]).effect, "   ");
  assert.equal(hasLine(result.text, "estado: estado-da-api"), true);
  assert.equal(hasLine(result.text, "aprovar"), false);
});

test("recusa da API e mostrada sem inventar estado", () => {
  const tracked = tracking({
    deny() {
      throw new SupervisionError("pendência sem efeito ou classe de risco");
    },
  });
  const result = deny_pending(tracked.api, sample());
  assert.equal(result.called, true);
  assert.equal(result.text, "recusa: pendência sem efeito ou classe de risco");
  assert.equal(result.approve_offered, false);
  assert.equal(result.text.includes("estado-da-api"), false);
});

test("erro que nao e recusa continua erro", () => {
  const tracked = tracking({
    approve() {
      throw new Error("falha");
    },
  });
  assert.throws(() => approve_pending(tracked.api, sample()), /falha/);
});

test("interromper chama a API e mostra o estado devolvido", () => {
  const tracked = tracking({
    interrupt_run() {
      return { run_id: "outro-run", status: "estado-devolvido", stop_reason: "motivo-devolvido" };
    },
  });
  const result = interrupt_run(tracked.api, "run-9");
  assert.equal(result.called, true);
  assert.equal(result.interrupt_offered, false);
  assert.equal(result.text, "run: outro-run\nestado: estado-devolvido\nmotivo: motivo-devolvido");
  assert.deepEqual(tracked.calls, [["interrupt_run", "run-9"]]);
});

test("interromper fica visivel no run ativo e nao troca o estado", () => {
  assert.equal(interrupt_offered("aberto"), true);
  assert.equal(interrupt_offered("encerrado"), false);
  assert.equal(interrupt_offered(""), false);
  const tracked = tracking({
    interrupt_run(runId) {
      return { run_id: runId, status: "aberto", stop_reason: "" };
    },
  });
  const result = interrupt_run(tracked.api, "run-9");
  assert.equal(result.interrupt_offered, true);
  assert.equal(result.text, "run: run-9\nestado: aberto\nmotivo: ");
});

test("run ativo mostra interromper mesmo sem pendencia", () => {
  const idle = tracking();
  const screen = open_supervision(idle.api, "run-1", "aberto");
  assert.equal(screen.interrupt_offered, true);
  assert.equal(screen.pending.length, 0);
  assert.equal(screen.text, "interromper");
  assert.deepEqual(idle.calls, [["list_pending", "run-1"]]);
  const closed = tracking();
  const hidden = open_supervision(closed.api, "run-1", "encerrado");
  assert.equal(hidden.interrupt_offered, false);
  assert.equal(hidden.text, "");
});

test("a lista preserva a ordem e nao filtra pela classe", () => {
  const tracked = tracking({
    list_pending() {
      return [
        sample({ action: "primeira", risk_class: "zzz" }),
        sample({ action: "segunda", risk_class: "aaa", effect: "" }),
      ];
    },
  });
  const screen = open_supervision(tracked.api, "run-7", "aberto");
  assert.equal(screen.pending[0]?.action, "primeira");
  assert.equal(screen.pending[1]?.action, "segunda");
  assert.equal(screen.pending[0]?.approve_offered, true);
  assert.equal(screen.pending[1]?.approve_offered, false);
  assert.equal(screen.pending[1]?.risk_class, "aaa");
  assert.equal(screen.text.endsWith("\ninterromper"), true);
  assert.equal(
    tracked.calls.some((call) => call[0] === "approve" || call[0] === "deny"),
    false,
  );
});
