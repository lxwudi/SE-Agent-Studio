import api from "./http";
import type { FlowRun, RunEvent, TaskRun } from "../types";


export function createRun(projectUid: string, payload: { requirement_text: string; workflow_code?: string }) {
  return api.post<FlowRun>(`/api/v1/projects/${projectUid}/runs`, payload);
}

export function getRun(runUid: string) {
  return api.get<FlowRun>(`/api/v1/runs/${runUid}`);
}

export function listRunTasks(runUid: string) {
  return api.get<TaskRun[]>(`/api/v1/runs/${runUid}/tasks`);
}

export function listRunEvents(runUid: string) {
  return api.get<RunEvent[]>(`/api/v1/runs/${runUid}/events`);
}

export function cancelRun(runUid: string) {
  return api.post<FlowRun>(`/api/v1/runs/${runUid}/cancel`);
}

export function resumeRun(runUid: string) {
  return api.post<FlowRun>(`/api/v1/runs/${runUid}/resume`);
}

