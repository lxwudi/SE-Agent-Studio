import api from "./http";
import type { DiscoverModelsResponse, UserLLMConfig } from "../types";


export function getLLMConfig() {
  return api.get<UserLLMConfig>("/api/v1/llm-config");
}

export function updateLLMConfig(payload: {
  provider_name?: string;
  base_url?: string;
  default_model?: string;
  agent_model_overrides?: Record<string, string>;
  agent_overrides?: Record<string, {
    override_enabled: boolean;
    provider_name?: string;
    base_url?: string;
    default_model?: string;
    api_key?: string;
    clear_api_key?: boolean;
  }>;
  api_key?: string;
  enabled?: boolean;
  clear_api_key?: boolean;
}) {
  return api.put<UserLLMConfig>("/api/v1/llm-config", payload);
}

export function discoverLLMModels(payload: {
  agent_code?: string;
  provider_name?: string;
  base_url?: string;
  api_key?: string;
}) {
  return api.post<DiscoverModelsResponse>("/api/v1/llm-config/discover-models", payload);
}
