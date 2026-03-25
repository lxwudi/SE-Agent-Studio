import { defineStore } from "pinia";
import { ref } from "vue";

import { getArtifact, listProjectArtifacts } from "../api/artifacts";
import type { Artifact, ArtifactDetail } from "../types";


export const useArtifactStore = defineStore("artifactStore", () => {
  const artifacts = ref<Artifact[]>([]);
  const selectedArtifact = ref<ArtifactDetail | null>(null);
  const loading = ref(false);

  async function fetchArtifacts(projectUid: string) {
    loading.value = true;
    try {
      const { data } = await listProjectArtifacts(projectUid);
      artifacts.value = data;
    } finally {
      loading.value = false;
    }
  }

  async function fetchArtifact(artifactUid: string) {
    const { data } = await getArtifact(artifactUid);
    selectedArtifact.value = data;
  }

  return {
    artifacts,
    selectedArtifact,
    loading,
    fetchArtifacts,
    fetchArtifact,
  };
});

