<template>
  <div class="page">
    <div class="page-header">
      <div>
        <p class="eyebrow">产物中心</p>
        <h2>结构化产物中心</h2>
        <p>把需求、架构、前后端设计、AI 方案和测试计划集中放到同一个阅读界面里。</p>
      </div>
      <div class="badge-row">
        <span class="chip">已归档 {{ artifactStore.artifacts.length }} 份</span>
      </div>
    </div>

    <div class="section-grid">
      <div class="span-5">
        <div class="glass-panel section-panel">
          <div class="section-heading">
            <div>
              <h3 class="card-title">产物列表</h3>
              <p class="helper-text">左侧按文档类型浏览，点击后在右侧查看对应内容。</p>
            </div>
            <span class="chip">目录</span>
          </div>
          <ArtifactGroup
            :artifacts="artifactStore.artifacts"
            :selected-artifact-uid="artifactStore.selectedArtifact?.artifact_uid"
            @select="selectArtifact"
          />
        </div>
      </div>

      <div class="span-7">
        <div class="glass-panel preview-card">
          <div class="section-heading">
            <div>
              <h3 class="card-title">文档内容</h3>
              <p class="helper-text">当前展示文档正文，后续可以继续补充更丰富的预览方式。</p>
            </div>
            <span v-if="artifactStore.selectedArtifact" class="chip">
              {{ getArtifactTypeLabel(artifactStore.selectedArtifact.artifact_type) }}
            </span>
          </div>

          <div v-if="artifactStore.selectedArtifact" class="markdown-shell">
            <pre>{{ artifactStore.selectedArtifact.content_markdown }}</pre>
          </div>

          <div v-else class="mini-card empty-state">
            <h4>请选择左侧文档</h4>
            <p>选择后会在右侧展示对应内容。</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRoute } from "vue-router";

import ArtifactGroup from "../components/ArtifactGroup.vue";
import { useArtifactStore } from "../stores/artifact";
import { getArtifactTypeLabel } from "../utils/presentation";


const route = useRoute();
const artifactStore = useArtifactStore();
const projectUid = computed(() => String(route.params.projectUid));

onMounted(async () => {
  await artifactStore.fetchArtifacts(projectUid.value);
  if (artifactStore.artifacts.length && !artifactStore.selectedArtifact) {
    await artifactStore.fetchArtifact(artifactStore.artifacts[0].artifact_uid);
  }
});

async function selectArtifact(artifactUid: string) {
  await artifactStore.fetchArtifact(artifactUid);
}
</script>
