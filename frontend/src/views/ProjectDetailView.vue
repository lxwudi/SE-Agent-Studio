<template>
  <div class="page" v-if="projectStore.currentProject">
    <div class="page-header">
      <div>
        <p class="eyebrow">项目工作台</p>
        <h2>{{ projectStore.currentProject.name }}</h2>
        <p>{{ projectStore.currentProject.description || "在这里补充项目背景、完善需求，并发起新的设计任务。" }}</p>
      </div>

      <div class="badge-row">
        <span class="chip">最近运行 {{ projectStore.currentProject.recent_run_uids.length }} 次</span>
        <el-button @click="goArtifacts">产物中心</el-button>
      </div>
    </div>

    <div class="run-summary-grid">
      <div class="glass-panel metric-card metric-card--accent">
        <small>需求字数</small>
        <strong>{{ requirementText.length }}</strong>
        <p>输入内容越完整，生成的设计结果通常越清晰。</p>
      </div>

      <div class="glass-panel metric-card">
        <small>运行记录</small>
        <strong>{{ projectStore.currentProject.recent_run_uids.length }}</strong>
        <p>这里会保留最近几次任务，方便快速回看进度和成果。</p>
      </div>

      <div class="glass-panel metric-card">
        <small>成果形式</small>
        <strong>文档化</strong>
        <p>每个阶段都会沉淀为可阅读、可下载的设计文档。</p>
      </div>
    </div>

    <div class="section-grid">
      <div class="span-7">
        <div class="glass-panel editor-card">
          <div class="section-heading">
            <div>
              <h3 class="card-title">需求编辑器</h3>
              <p class="helper-text">把项目目标、功能范围和约束条件整理清楚，系统会生成对应设计文档。</p>
            </div>
            <span class="chip">需求输入</span>
          </div>

          <el-input
            v-model="requirementText"
            type="textarea"
            :rows="18"
            placeholder="输入自然语言需求描述..."
          />

          <div class="badge-row" style="margin-top: 18px; justify-content: space-between">
            <span class="helper-text">建议写清目标用户、核心功能、约束条件和非功能需求。</span>
            <el-button type="primary" @click="handleCreateRun">启动运行</el-button>
          </div>
        </div>
      </div>

      <div class="span-5">
        <div class="glass-panel section-panel">
          <div class="section-heading">
            <div>
              <h3 class="card-title">最近运行</h3>
              <p class="helper-text">从这里查看每次任务的进度、异常情况和最终成果。</p>
            </div>
            <span class="chip">历史记录</span>
          </div>

          <div class="list-stack">
            <RouterLink
              v-for="runUid in projectStore.currentProject.recent_run_uids"
              :key="runUid"
              :to="`/runs/${runUid}`"
              class="mini-card"
            >
              <h4>{{ runUid }}</h4>
              <p>进入详情页查看这次任务的阶段进展、异常和设计文档。</p>
            </RouterLink>

            <div v-if="!projectStore.currentProject.recent_run_uids.length" class="mini-card empty-state">
              <h4>还没有运行记录</h4>
              <p>把左侧需求整理好后，先启动第一条工作流。</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { useProjectStore } from "../stores/project";
import { useRunStore } from "../stores/run";


const route = useRoute();
const router = useRouter();
const projectStore = useProjectStore();
const runStore = useRunStore();

const projectUid = computed(() => String(route.params.projectUid));
const requirementText = ref("");

onMounted(async () => {
  await projectStore.fetchProject(projectUid.value);
  requirementText.value = projectStore.currentProject?.latest_requirement ?? "";
});

async function handleCreateRun() {
  if (!requirementText.value.trim()) {
    ElMessage.warning("请先输入项目需求。");
    return;
  }
  const run = await runStore.create(projectUid.value, requirementText.value);
  router.push(`/runs/${run.run_uid}`);
}

function goArtifacts() {
  router.push(`/projects/${projectUid.value}/artifacts`);
}
</script>
