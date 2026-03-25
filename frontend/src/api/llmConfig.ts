import api from "./http";
import type { UserLLMConfig } from "../types";


export function getLLMConfig() {
  return api.get<UserLLMConfig>("/api/v1/llm-config");
}

export function updateLLMConfig(payload: {
  provider_name?: string;
  base_url?: string;
  default_model?: string;
  api_key?: string;
  enabled?: boolean;
  clear_api_key?: boolean;
}) {
  return api.put<UserLLMConfig>("/api/v1/llm-config", payload);
}
