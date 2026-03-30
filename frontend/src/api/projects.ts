import api from "./http";
import type { Project, ProjectDetail } from "../types";


export function listProjects() {
  return api.get<Project[]>("/api/v1/projects");
}

export function createProject(payload: {
  name: string;
  description: string;
  latest_requirement: string;
}) {
  return api.post<Project>("/api/v1/projects", payload);
}

export function getProject(projectUid: string) {
  return api.get<ProjectDetail>(`/api/v1/projects/${projectUid}`);
}

export function updateProject(
  projectUid: string,
  payload: Partial<{ name: string; description: string; latest_requirement: string }>
) {
  return api.patch<Project>(`/api/v1/projects/${projectUid}`, payload);
}

export function deleteProject(projectUid: string) {
  return api.delete(`/api/v1/projects/${projectUid}`);
}

export function downloadProjectPackage(projectUid: string) {
  return api.get<Blob>(`/api/v1/projects/${projectUid}/package`, {
    responseType: "blob",
  });
}
