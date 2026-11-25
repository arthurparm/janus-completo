import { is_json_object } from "../../src/janus/util/json_object.ts";

// A tela repete o que a API devolveu. Não escolhe ferramenta nem calcula risco.
export class SupervisionError extends Error {
  readonly reason: string;

  constructor(reason: string) {
    super(reason);
    this.name = "SupervisionError";
    this.reason = reason;
  }
}

export type PendingPayload = {
  readonly action: string;
  readonly arguments_hash: string;
  readonly deadline_ms: number;
  readonly effect: string;
  readonly idempotency_key: string;
  readonly opened_at: string;
  readonly risk_class: string;
  readonly run_id: string;
  readonly status: string;
  readonly tool_name: string;
};

export type RunPayload = {
  readonly run_id: string;
  readonly status: string;
  readonly stop_reason: string;
};

export type SupervisionApi = {
  list_pending(run_id: string): readonly unknown[];
  approve(pending: PendingPayload): unknown;
  deny(pending: PendingPayload): unknown;
  interrupt_run(run_id: string): unknown;
};

export type PendingView = {
  readonly action: string;
  readonly approve_offered: boolean;
  readonly deny_offered: boolean;
  readonly effect: string;
  readonly risk_class: string;
  readonly status: string;
  readonly text: string;
};

export type CommandResult = {
  readonly approve_offered: boolean;
  readonly called: boolean;
  readonly deny_offered: boolean;
  readonly text: string;
};

export type RunResult = {
  readonly called: boolean;
  readonly interrupt_offered: boolean;
  readonly text: string;
};

export type SupervisionScreen = {
  readonly interrupt_offered: boolean;
  readonly pending: readonly PendingView[];
  readonly text: string;
};

function _text_field(source: Readonly<Record<string, unknown>>, key: string): string | null {
  const value = source[key];
  return typeof value === "string" ? value : null;
}

function _filled(value: string): boolean {
  return value.trim() !== "";
}

// Controle, formato, surrogate e separador de linha ou parágrafo.
const HIDDEN_CHAR = /[\p{Cc}\p{Cf}\p{Cs}\p{Zl}\p{Zp}]/u;

function _direct(value: string): boolean {
  return _filled(value) && !HIDDEN_CHAR.test(value);
}

function _visible(value: string): string {
  let visible = "";
  for (const char of value) {
    if (HIDDEN_CHAR.test(char)) {
      visible += "\\u" + (char.codePointAt(0) ?? 0).toString(16).padStart(4, "0");
    } else {
      visible += char;
    }
  }
  return visible;
}

function _can_approve(pending: PendingPayload): boolean {
  return _direct(pending.action) && _direct(pending.effect) && _direct(pending.risk_class);
}

function _read_pending(value: unknown): PendingPayload | null {
  if (!is_json_object(value)) {
    return null;
  }
  const action = _text_field(value, "action");
  const argumentsHash = _text_field(value, "arguments_hash");
  const effect = _text_field(value, "effect");
  const idempotencyKey = _text_field(value, "idempotency_key");
  const openedAt = _text_field(value, "opened_at");
  const risk_class = _text_field(value, "risk_class");
  const run_id = _text_field(value, "run_id");
  const status = _text_field(value, "status");
  const toolName = _text_field(value, "tool_name");
  const deadline = value.deadline_ms;
  if (
    action === null ||
    argumentsHash === null ||
    effect === null ||
    idempotencyKey === null ||
    openedAt === null ||
    risk_class === null ||
    run_id === null ||
    status === null ||
    toolName === null ||
    typeof deadline !== "number" ||
    !Number.isInteger(deadline) ||
    deadline < 0
  ) {
    return null;
  }
  return {
    action,
    arguments_hash: argumentsHash,
    deadline_ms: deadline,
    effect,
    idempotency_key: idempotencyKey,
    opened_at: openedAt,
    risk_class: risk_class,
    run_id: run_id,
    status,
    tool_name: toolName,
  };
}

function _loose_text(value: unknown, key: string): string {
  if (!is_json_object(value)) {
    return "";
  }
  const item = value[key];
  return typeof item === "string" ? item : "";
}

export function approve_offered(value: unknown): boolean {
  const pending = _read_pending(value);
  return pending !== null && _can_approve(pending);
}

function _deny_offered(value: unknown): boolean {
  return _read_pending(value) !== null;
}

function _render_pending(
  action: string,
  effect: string,
  risk_class: string,
  status: string,
  approve: boolean,
  deny: boolean,
): string {
  const lines = [
    `ação: ${_visible(action)}`,
    `efeito: ${_visible(effect)}`,
    `risco: ${_visible(risk_class)}`,
    `estado: ${_visible(status)}`,
  ];
  if (approve) {
    lines.push("aprovar");
  }
  if (deny) {
    lines.push("negar");
  }
  return lines.join("\n");
}

export function view_pending(value: unknown): PendingView {
  const action = _loose_text(value, "action");
  const effect = _loose_text(value, "effect");
  const risk_class = _loose_text(value, "risk_class");
  const status = _loose_text(value, "status");
  const canApprove = approve_offered(value);
  const canDeny = _deny_offered(value);
  return {
    action,
    approve_offered: canApprove,
    deny_offered: canDeny,
    effect,
    risk_class,
    status,
    text: _render_pending(action, effect, risk_class, status, canApprove, canDeny),
  };
}

function _command_from(view: PendingView, called: boolean): CommandResult {
  return {
    approve_offered: view.approve_offered,
    called,
    deny_offered: view.deny_offered,
    text: view.text,
  };
}

function _call_pending(
  value: unknown,
  send: (pending: PendingPayload) => unknown,
  allowed: (pending: PendingPayload) => boolean,
): CommandResult {
  const pending = _read_pending(value);
  if (pending === null || !allowed(pending)) {
    return _command_from(view_pending(value), false);
  }
  try {
    return _command_from(view_pending(send(pending)), true);
  } catch (error) {
    if (error instanceof SupervisionError) {
      return {
        approve_offered: false,
        called: true,
        deny_offered: false,
        text: `recusa: ${error.reason}`,
      };
    }
    throw error;
  }
}

export function approve_pending(api: SupervisionApi, pending: unknown): CommandResult {
  return _call_pending(
    pending,
    (item) => api.approve(item),
    (item) => _can_approve(item),
  );
}

export function deny_pending(api: SupervisionApi, pending: unknown): CommandResult {
  return _call_pending(pending, (item) => api.deny(item), () => true);
}

function _read_run(value: unknown): RunPayload | null {
  if (!is_json_object(value)) {
    return null;
  }
  const run_id = value.run_id;
  const status = value.status;
  const stopReason = value.stop_reason;
  if (typeof run_id !== "string" || typeof status !== "string" || typeof stopReason !== "string") {
    return null;
  }
  return { run_id: run_id, status, stop_reason: stopReason };
}

export function show_run(value: unknown): string {
  const run = _read_run(value);
  if (run === null) {
    return "";
  }
  return `run: ${run.run_id}\nestado: ${run.status}\nmotivo: ${run.stop_reason}`;
}

export function interrupt_offered(run_status: string): boolean {
  return run_status === "aberto";
}

export function interrupt_run(api: SupervisionApi, run_id: string): RunResult {
  try {
    const returned = api.interrupt_run(run_id);
    const run = _read_run(returned);
    return {
      called: true,
      interrupt_offered: run !== null && interrupt_offered(run.status),
      text: show_run(returned),
    };
  } catch (error) {
    if (error instanceof SupervisionError) {
      return { called: true, interrupt_offered: false, text: `recusa: ${error.reason}` };
    }
    throw error;
  }
}

export function open_supervision(
  api: SupervisionApi,
  run_id: string,
  run_status: string,
): SupervisionScreen {
  const pending = api.list_pending(run_id).map((item) => view_pending(item));
  const offered = interrupt_offered(run_status);
  const lines = pending.map((item) => item.text);
  if (offered) {
    lines.push("interromper");
  }
  return { interrupt_offered: offered, pending, text: lines.join("\n") };
}
