import type { BotEmoteName, BotStateName } from "./layout";
import type { EyeShape } from "../mochi/engine";

export interface AgentTask {
  id: string;
  name: string;
  color: string;
  state: BotStateName;
  stepIndex?: number;
  steps?: string[];
  emote?: BotEmoteName | null;
  miniEye?: EyeShape | null;
}
