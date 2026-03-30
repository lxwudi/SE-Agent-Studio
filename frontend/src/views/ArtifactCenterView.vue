<template>
  <div class="page">
    <div class="page-header">
      <div>
        <p class="eyebrow">交付产物</p>
        <h2>交付产物中心</h2>
        <p>默认优先展示最接近最终交付的内容，让你先知道这份结果怎么启动、怎么验证、接下来该做什么。</p>
      </div>
      <div class="badge-row">
        <span class="chip">已归档 {{ artifactStore.artifacts.length }} 份</span>
        <span v-if="recommendedArtifactLabel" class="chip">推荐先看 {{ recommendedArtifactLabel }}</span>
      </div>
    </div>

    <div class="section-grid">
      <div class="span-4">
        <div class="glass-panel section-panel">
          <div class="section-heading">
            <div>
              <h3 class="card-title">产物列表</h3>
              <p class="helper-text">左侧从最接近最终交付的产物开始排序，避免一上来就掉进内部文档。</p>
            </div>
            <span class="chip">目录</span>
          </div>
          <ArtifactGroup
            :artifacts="orderedArtifacts"
            :selected-artifact-uid="artifactStore.selectedArtifact?.artifact_uid"
            @select="selectArtifact"
          />
        </div>
      </div>

      <div class="span-8">
        <div class="glass-panel preview-card">
          <div class="section-heading">
            <div>
              <h3 class="card-title">交付预览</h3>
              <p class="helper-text">这里把可运行信息、下一步和生成文件合并成一个可连续阅读的交付界面。</p>
            </div>
            <span v-if="artifactStore.selectedArtifact" class="chip">
              {{ getArtifactTypeLabel(artifactStore.selectedArtifact.artifact_type) }}
            </span>
          </div>

          <div v-if="artifactStore.selectedArtifact" class="list-stack">
            <div class="insight-grid">
              <div class="mini-card insight-card">
                <small>当前产物</small>
                <strong>{{ getArtifactTypeLabel(artifactStore.selectedArtifact.artifact_type) }}</strong>
                <p>{{ artifactStore.selectedArtifact.title }}</p>
              </div>
              <div class="mini-card insight-card">
                <small>工作区</small>
                <strong>{{ workspaceRoot ? "已落盘" : "未提供" }}</strong>
                <p>{{ workspaceRoot || "这份产物没有附带工作区路径。" }}</p>
              </div>
              <div class="mini-card insight-card">
                <small>生成文件</small>
                <strong>{{ generatedFiles.length }}</strong>
                <p>{{ generatedFiles.length ? generatedFiles.slice(0, 3).map((item) => item.path).join(" · ") : "当前产物不包含文件正文。" }}</p>
              </div>
              <div class="mini-card insight-card">
                <small>验证结果</small>
                <strong>{{ verificationSummary }}</strong>
                <p>{{ verificationDetail }}</p>
              </div>
            </div>

            <div v-if="workspaceRoot" class="mini-card">
              <h4>工作区位置</h4>
              <p>{{ workspaceRoot }}</p>
            </div>

            <div class="section-grid delivery-preview-grid">
              <div v-if="startupGuide.length" class="span-6">
                <div class="mini-card">
                  <h4>如何启动</h4>
                  <ul class="delivery-list">
                    <li v-for="item in startupGuide" :key="item">{{ item }}</li>
                  </ul>
                </div>
              </div>

              <div v-if="nextSteps.length" class="span-6">
                <div class="mini-card">
                  <h4>下一步建议</h4>
                  <ul class="delivery-list">
                    <li v-for="item in nextSteps" :key="item">{{ item }}</li>
                  </ul>
                </div>
              </div>

              <div v-if="supportingHighlights.length" class="span-12">
                <div class="mini-card">
                  <h4>{{ supportingHighlightsTitle }}</h4>
                  <ul class="delivery-list">
                    <li v-for="item in supportingHighlights" :key="item">{{ item }}</li>
                  </ul>
                </div>
              </div>

              <div v-if="runCommands.length" class="span-6">
                <div class="mini-card">
                  <h4>推荐启动命令</h4>
                  <div class="command-grid">
                    <div v-for="command in runCommands" :key="`${command.label}-${command.command}`" class="command-card">
                      <strong>{{ command.label }}</strong>
                      <p>{{ command.purpose }}</p>
                      <div class="markdown-shell">
                        <pre>{{ command.command }}</pre>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div v-if="validationCommands.length" class="span-6">
                <div class="mini-card">
                  <h4>推荐验证命令</h4>
                  <div class="command-grid">
                    <div v-for="command in validationCommands" :key="`${command.label}-${command.command}`" class="command-card">
                      <strong>{{ command.label }}</strong>
                      <p>{{ command.purpose }}</p>
                      <div class="markdown-shell">
                        <pre>{{ command.command }}</pre>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="generatedFiles.length" class="list-stack">
              <div class="section-heading">
                <div>
                  <h4 class="card-title">生成文件</h4>
                  <p class="helper-text">文件正文直接展示在这里，避免你在多个产物之间跳来跳去。</p>
                </div>
                <span class="chip">共 {{ generatedFiles.length }} 份</span>
              </div>

              <div class="badge-row">
                <el-button
                  v-for="file in generatedFiles"
                  :key="file.path"
                  size="small"
                  :type="file.path === selectedGeneratedFilePath ? 'primary' : 'default'"
                  plain
                  @click="selectedGeneratedFilePath = file.path"
                >
                  {{ file.path }}
                </el-button>
              </div>

              <div v-if="currentGeneratedFile" class="mini-card">
                <h4>{{ currentGeneratedFile.path }}</h4>
                <p>{{ currentGeneratedFile.purpose || currentGeneratedFile.language || "生成文件" }}</p>
              </div>

              <div class="markdown-shell">
                <pre>{{ currentGeneratedFile?.content ?? "" }}</pre>
              </div>
            </div>

            <div v-if="verificationResults.length" class="list-stack">
              <div class="section-heading">
                <div>
                  <h4 class="card-title">自动验证结果</h4>
                  <p class="helper-text">这些检查已经在交付流程内执行过，可以直接拿来判断这份产物是否达标。</p>
                </div>
                <span class="chip">通过 {{ passedVerificationCount }}/{{ verificationResults.length }}</span>
              </div>

              <div
                v-for="result in verificationResults"
                :key="`${result.label}-${result.command}`"
                class="mini-card"
              >
                <h4>{{ result.label }} · {{ result.success ? "通过" : "失败" }}</h4>
                <p>{{ result.summary }}</p>
                <div class="markdown-shell">
                  <pre>{{ result.command }}</pre>
                </div>
                <div v-if="result.output" class="markdown-shell" style="margin-top: 12px">
                  <pre>{{ result.output }}</pre>
                </div>
              </div>
            </div>

            <div v-if="artifactStore.selectedArtifact.content_markdown.trim()" class="list-stack">
              <div class="section-heading">
                <div>
                  <h4 class="card-title">原始正文</h4>
                  <p class="helper-text">保留完整原文，方便继续核对模型生成的说明内容。</p>
                </div>
                <span class="chip">原文</span>
              </div>
              <div class="markdown-shell">
                <pre>{{ artifactStore.selectedArtifact.content_markdown }}</pre>
              </div>
            </div>
          </div>

          <div v-else class="mini-card empty-state">
            <h4>还没有可预览的产物</h4>
            <p>左侧出现产物后，这里会优先展示最接近最终交付的内容。</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

import ArtifactGroup from "../components/ArtifactGroup.vue";
import { useArtifactStore } from "../stores/artifact";
import type { DeliveryGeneratedFile } from "../types";
import {
  asRecord,
  extractCommandSpecs,
  extractFirstStringList,
  extractGeneratedFiles,
  extractVerificationResults,
  extractWorkspaceRoot,
  getPreferredArtifact,
  sortArtifactsByPriority,
} from "../utils/delivery";
import { getArtifactTypeLabel } from "../utils/presentation";


const route = useRoute();
const artifactStore = useArtifactStore();
const projectUid = computed(() => String(route.params.projectUid));
const selectedGeneratedFilePath = ref("");
const orderedArtifacts = computed(() => sortArtifactsByPriority(artifactStore.artifacts));
const recommendedArtifactLabel = computed(() => {
  const preferred = getPreferredArtifact(artifactStore.artifacts);
  return preferred ? getArtifactTypeLabel(preferred.artifact_type) : "";
});
const selectedContent = computed(() => asRecord(artifactStore.selectedArtifact?.content_json));
const generatedFiles = computed(() => extractGeneratedFiles(selectedContent.value.files));
const verificationResults = computed(() => extractVerificationResults(selectedContent.value.verification_results));
const startupGuide = computed(() => extractFirstStringList(selectedContent.value, ["startup_guide", "startup_steps"]));
const nextSteps = computed(() => extractFirstStringList(selectedContent.value, ["next_steps", "delivery_notes", "verification_status", "notes"]));
const supportingHighlights = computed(() => {
  return extractFirstStringList(selectedContent.value, [
    "setup_notes",
    "implementation_order",
    "workspace_layout",
    "core_capabilities",
    "acceptance_criteria",
  ]);
});
const supportingHighlightsTitle = computed(() => {
  if (selectedContent.value.setup_notes) {
    return "补充说明";
  }
  if (selectedContent.value.implementation_order) {
    return "实施顺序";
  }
  if (selectedContent.value.workspace_layout) {
    return "目录结构";
  }
  if (selectedContent.value.core_capabilities) {
    return "核心能力";
  }
  return "验收要点";
});
const runCommands = computed(() => extractCommandSpecs(selectedContent.value.run_commands));
const validationCommands = computed(() => extractCommandSpecs(selectedContent.value.validation_commands));
const currentGeneratedFile = computed<DeliveryGeneratedFile | null>(() => {
  if (!generatedFiles.value.length) {
    return null;
  }
  return generatedFiles.value.find((item) => item.path === selectedGeneratedFilePath.value) ?? generatedFiles.value[0];
});
const passedVerificationCount = computed(() => verificationResults.value.filter((item) => item.success).length);
const verificationSummary = computed(() => {
  if (!verificationResults.value.length) {
    return validationCommands.value.length ? `命令 ${validationCommands.value.length}` : "暂无";
  }
  return `${passedVerificationCount.value}/${verificationResults.value.length} 通过`;
});
const verificationDetail = computed(() => {
  if (verificationResults.value.length) {
    return verificationResults.value.map((item) => `${item.label}${item.success ? "通过" : "失败"}`).join("，");
  }
  if (validationCommands.value.length) {
    return "当前产物提供了验证命令，可以按需手动执行。";
  }
  return "当前产物没有附带自动验证结果。";
});
const workspaceRoot = computed(() => extractWorkspaceRoot(selectedContent.value));

onMounted(async () => {
  await artifactStore.fetchArtifacts(projectUid.value);
  const preferred = getPreferredArtifact(artifactStore.artifacts);
  if (preferred) {
    await artifactStore.fetchArtifact(preferred.artifact_uid);
  }
});

async function selectArtifact(artifactUid: string) {
  await artifactStore.fetchArtifact(artifactUid);
}

watch(
  generatedFiles,
  (files) => {
    if (!files.length) {
      selectedGeneratedFilePath.value = "";
      return;
    }
    if (!files.some((item) => item.path === selectedGeneratedFilePath.value)) {
      selectedGeneratedFilePath.value = files[0].path;
    }
  },
  { immediate: true },
);
</script>
