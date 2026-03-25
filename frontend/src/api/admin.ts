import api from "./http";
import type { AgentProfile, WorkflowTemplate } from "../types";


export function listAgents() {
  return api.get<AgentProfile[]>("/api/v1/admin/agents");
}

export function listWorkflows() {
  return api.get<WorkflowTemplate[]>("/api/v1/admin/workflows");
}

