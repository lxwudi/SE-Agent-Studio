import api from "./http";
import type { Artifact, ArtifactDetail } from "../types";


export function listProjectArtifacts(projectUid: string) {
  return api.get<Artifact[]>(`/api/v1/projects/${projectUid}/artifacts`);
}

export function getArtifact(artifactUid: string) {
  return api.get<ArtifactDetail>(`/api/v1/artifacts/${artifactUid}`);
}

