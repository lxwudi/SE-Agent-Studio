export interface Project {
  uid: string;
  name: string;
  description: string;
  latest_requirement: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectDetail extends Project {
  recent_run_uids: string[];
}

export interface FlowRun {
  run_uid: string;
  status: string;
  current_stage: string;
  input_requirement: string;
  state_json: Record<string, unknown>;
  error_message: string;
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface TaskRun {
  task_uid: string;
  step_code: string;
  agent_code: string;
  crew_name: string;
  status: string;
  input_json: Record<string, unknown>;
  output_json: Record<string, unknown>;
  output_text: string;
  error_message: string;
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface RunEvent {
  id: number;
  event_type: string;
  event_source: string;
  payload_json: Record<string, unknown>;
  created_at: string;
}

export interface Artifact {
  artifact_uid: string;
  artifact_type: string;
  title: string;
  version_no: number;
  created_at: string;
}

export interface ArtifactDetail extends Artifact {
  content_markdown: string;
  content_json: Record<string, unknown>;
}

export interface AgentProfile {
  agent_code: string;
  display_name: string;
  description: string;
  source_file: string;
  default_model: string;
  temperature: number;
  allow_delegation: boolean;
  enabled: boolean;
  meta_json: Record<string, unknown>;
}

export interface WorkflowStep {
  step_code: string;
  step_type: string;
  agent_code?: string | null;
  depends_on: string[];
  parallel_group?: string | null;
  output_schema?: string | null;
  sort_order: number;
}

export interface WorkflowTemplate {
  workflow_code: string;
  name: string;
  description: string;
  version: number;
  enabled: boolean;
  config_json: Record<string, unknown>;
  steps: WorkflowStep[];
}

export interface AuthUser {
  uid: string;
  email: string;
  display_name: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

export interface UserLLMConfig {
  provider_name: string;
  base_url: string;
  default_model: string;
  enabled: boolean;
  has_api_key: boolean;
  masked_api_key: string;
  is_ready: boolean;
  updated_at?: string | null;
}
