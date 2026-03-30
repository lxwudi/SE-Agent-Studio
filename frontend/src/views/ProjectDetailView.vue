<template>
  <div class="page" v-if="projectStore.currentProject">
    <div class="page-header">
      <div>
        <p class="eyebrow">项目工作台</p>
        <h2>{{ projectStore.currentProject.name }}</h2>
        <p>{{ projectStore.currentProject.description || "在这里补充项目背景、完善需求，并发起新的代码交付任务。" }}</p>
      </div>

      <div class="badge-row">
        <span class="chip">最近运行 {{ projectStore.currentProject.recent_run_uids.length }} 次</span>
        <el-button type="primary" :loading="downloadingPackage" @click="handleDownloadPackage">下载项目压缩包</el-button>
        <el-button plain @click="goArtifacts">查看细节</el-button>
        <el-button type="danger" plain :loading="deleting" @click="handleDelete">删除项目</el-button>
      </div>
    </div>

    <div class="run-summary-grid">
      <div class="glass-panel metric-card metric-card--accent">
        <small>需求字数</small>
        <strong>{{ requirementText.length }}</strong>
        <p>输入内容越完整，生成的代码交付结果通常越贴近预期。</p>
      </div>

      <div class="glass-panel metric-card">
        <small>运行记录</small>
        <strong>{{ projectStore.currentProject.recent_run_uids.length }}</strong>
        <p>这里会保留最近几次任务，方便快速回看进度和成果。</p>
      </div>

      <div class="glass-panel metric-card">
        <small>成果形式</small>
        <strong>代码交付</strong>
        <p>每个阶段都会沉淀为可阅读的产物，集成阶段还会产出最终代码和验证结果。</p>
      </div>
    </div>

    <div class="section-grid">
      <div class="span-7">
        <div class="glass-panel editor-card">
          <div class="section-heading">
            <div>
              <h3 class="card-title">需求编辑器</h3>
              <p class="helper-text">把项目目标、功能范围和约束条件整理清楚，系统会生成对应代码交付产物。</p>
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
              :to="{ path: `/runs/${runUid}`, query: { projectUid } }"
              class="mini-card"
            >
              <h4>{{ runUid }}</h4>
              <p>进入详情页查看这次任务的阶段进展、异常、代码产物和验证结果。</p>
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
import { ElMessage, ElMessageBox } from "element-plus";
import axios from "axios";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { downloadProjectPackage } from "../api/projects";
import { useProjectStore } from "../stores/project";
import { useRunStore } from "../stores/run";
import { extractFilenameFromDisposition, triggerBlobDownload } from "../utils/download";


const route = useRoute();
const router = useRouter();
const projectStore = useProjectStore();
const runStore = useRunStore();

const projectUid = computed(() => String(route.params.projectUid));
const requirementText = ref("");
const deleting = ref(false);
const downloadingPackage = ref(false);

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
  router.push({ path: `/runs/${run.run_uid}`, query: { projectUid: projectUid.value } });
}

function goArtifacts() {
  router.push(`/projects/${projectUid.value}/artifacts`);
}

async function handleDownloadPackage() {
  downloadingPackage.value = true;
  try {
    const response = await downloadProjectPackage(projectUid.value);
    const filename = extractFilenameFromDisposition(response.headers["content-disposition"]) || "delivery-package.zip";
    triggerBlobDownload(response.data, filename);
    ElMessage.success("项目压缩包已开始下载。");
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      ElMessage.info("当前还没有可下载的项目压缩包，请先完成一次交付。");
    } else {
      ElMessage.error("下载项目压缩包失败，请稍后重试。");
    }
  } finally {
    downloadingPackage.value = false;
  }
}

async function handleDelete() {
  if (!projectStore.currentProject) {
    return;
  }

  try {
    await ElMessageBox.confirm(
      `删除后，这个项目下的运行记录和产物也会一起移除。确认删除“${projectStore.currentProject.name}”吗？`,
      "删除项目",
      {
        type: "warning",
        confirmButtonText: "确认删除",
        cancelButtonText: "取消",
      },
    );
  } catch {
    return;
  }

  deleting.value = true;
  try {
    await projectStore.remove(projectUid.value);
    ElMessage.success("项目已删除。");
    router.push("/projects");
  } catch {
    ElMessage.error("删除项目失败，请稍后重试。");
  } finally {
    deleting.value = false;
  }
}
</script>
