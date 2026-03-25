<template>
  <div class="artifact-list">
    <div
      v-for="artifact in artifacts"
      :key="artifact.artifact_uid"
      class="mini-card artifact-item"
      :class="{ 'is-active': artifact.artifact_uid === selectedArtifactUid }"
      @click="$emit('select', artifact.artifact_uid)"
    >
      <div class="card-header">
        <h4>{{ artifact.title }}</h4>
        <el-tag size="small">{{ getArtifactTypeLabel(artifact.artifact_type) }}</el-tag>
      </div>
      <div class="artifact-meta">
        <span>版本 {{ artifact.version_no }}</span>
        <span>{{ artifact.created_at }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Artifact } from "../types";
import { getArtifactTypeLabel } from "../utils/presentation";


defineProps<{
  artifacts: Artifact[];
  selectedArtifactUid?: string;
}>();

defineEmits<{
  (event: "select", artifactUid: string): void;
}>();
</script>
