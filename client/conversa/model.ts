import { is_json_object } from "../../src/janus/util/json_object.ts";

export class ConversationError extends Error {
  readonly reason: string;

  constructor(reason: string) {
    super(reason);
    this.name = "ConversationError";
    this.reason = reason;
  }
}

export type ConversationView = {
  readonly model_id: string;
  readonly notice: string;
  readonly task: string;
  readonly text: string;
};

export function show_conversation(identity: unknown): ConversationView {
  if (!is_json_object(identity) || identity.voice_is_model !== true) {
    throw new ConversationError("a entrada tem de registrar que a voz é um modelo");
  }
  const model = identity.model_id;
  if (typeof model !== "string" || model.trim() === "") {
    throw new ConversationError("a entrada tem de registrar que a voz é um modelo");
  }
  const model_id = model.trim();
  const task = typeof identity.task === "string" ? identity.task : "";
  const notice = `A voz é um modelo (${model_id}).`;
  return { model_id, notice, task, text: `${notice}\n${task}` };
}
