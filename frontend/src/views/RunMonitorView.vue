<template>
  <div class="page" v-if="runStore.currentRun">
    <div class="page-header">
      <div>
        <p class="eyebrow">交付进度</p>
        <h2>{{ runStore.currentRun.run_uid }}</h2>
        <p>先看这次交付能不能直接用，再决定是否继续下钻执行过程和内部事件。</p>
      </div>

      <div class="badge-row">
        <StatusTag :status="runStore.currentRun.status" />
        <el-button
          v-if="projectUid"
          type="primary"
          :loading="downloadingPackage"
          @click="handleDownloadPackage"
        >
          下载项目压缩包
        </el-button>
        <el-button v-if="projectUid" plain @click="goArtifacts">查看细节</el-button>
        <el-button @click="refresh">刷新状态</el-button>
        <el-button type="warning" :loading="resuming" :disabled="!canResume" @click="handleResume">继续执行</el-button>
        <el-button type="danger" plain :loading="cancelling" :disabled="!canCancel" @click="handleCancel">取消任务</el-button>
      </div>
    </div>

    <div v-if="isDeliveryRun" class="glass-panel delivery-spotlight">
      <div class="delivery-spotlight__header">
        <div>
          <p class="eyebrow">交付总览</p>
          <h3>{{ deliveryHeadline.title }}</h3>
          <p>{{ deliveryHeadline.description }}</p>
        </div>
        <div class="badge-row">
          <span v-if="deliveryWorkspaceRoot" class="chip">工作区已生成</span>
          <span v-if="fallbackCount" class="chip">模板兜底 {{ fallbackCount }} 次</span>
          <span v-if="repairCount" class="chip">自动修复 {{ repairCount }} 次</span>
        </div>
      </div>

      <div class="insight-grid">
        <div class="mini-card insight-card">
          <small>交付状态</small>
          <strong>{{ deliveryHeadline.badge }}</strong>
          <p>{{ runStore.currentRun.status === "COMPLETED" ? "当前 run 已完成归档。" : "系统仍在推进当前交付。" }}</p>
        </div>
        <div class="mini-card insight-card">
          <small>生成资产</small>
          <strong>{{ deliveryGeneratedAssets.length }}</strong>
          <p>{{ deliveryGeneratedAssets.length ? deliveryGeneratedAssets.slice(0, 3).join(" · ") : "工作区文件生成后会显示在这里。" }}</p>
        </div>
        <div class="mini-card insight-card">
          <small>自动验证</small>
          <strong>{{ deliveryVerificationSummary?.headline ?? "等待执行" }}</strong>
          <p>{{ deliveryVerificationSummary?.detail ?? "流程会在集成阶段补充自动验证结果。" }}</p>
        </div>
        <div class="mini-card insight-card">
          <small>当前阶段</small>
          <strong>{{ getStageLabel(runStore.currentRun.current_stage) }}</strong>
          <p>{{ fallbackCount || repairCount ? `兜底 ${fallbackCount} 次，修复 ${repairCount} 次。` : "当前没有触发兜底或自动修复。" }}</p>
        </div>
      </div>

      <div class="section-grid delivery-spotlight__grid">
        <div v-if="deliveryWorkspaceRoot" class="span-12">
          <div class="mini-card">
            <h4>工作区位置</h4>
            <p>{{ deliveryWorkspaceRoot }}</p>
          </div>
        </div>

        <div v-if="deliveryStartupGuide.length" class="span-6">
          <div class="mini-card">
            <h4>先这样启动</h4>
            <ul class="delivery-list">
              <li v-for="item in deliveryStartupGuide" :key="item">{{ item }}</li>
            </ul>
          </div>
        </div>

        <div v-if="deliveryNextSteps.length" class="span-6">
          <div class="mini-card">
            <h4>接下来建议</h4>
            <ul class="delivery-list">
              <li v-for="item in deliveryNextSteps" :key="item">{{ item }}</li>
            </ul>
          </div>
        </div>

        <div v-if="deliveryRunCommands.length" class="span-6">
          <div class="mini-card">
            <h4>推荐启动命令</h4>
            <div class="command-grid">
              <div v-for="command in deliveryRunCommands" :key="`${command.label}-${command.command}`" class="command-card">
                <strong>{{ command.label }}</strong>
                <p>{{ command.purpose }}</p>
                <div class="markdown-shell">
                  <pre>{{ command.command }}</pre>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="deliveryValidationCommands.length" class="span-6">
          <div class="mini-card">
            <h4>推荐验证命令</h4>
            <div class="command-grid">
              <div v-for="command in deliveryValidationCommands" :key="`${command.label}-${command.command}`" class="command-card">
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
    </div>

    <div class="run-summary-grid">
      <div class="glass-panel metric-card metric-card--accent">
        <small>当前阶段</small>
        <strong>{{ getStageLabel(runStore.currentRun.current_stage) }}</strong>
        <p>系统会持续更新当前所处阶段，便于判断是生成中、验证中，还是已经可接收。</p>
      </div>

      <div class="glass-panel metric-card">
        <small>执行步骤</small>
        <strong>{{ runStore.tasks.length }}</strong>
        <p>保留所有阶段执行记录，方便后续排障和对比不同 run 的表现。</p>
      </div>

      <div class="glass-panel metric-card">
        <small>动态更新</small>
        <strong>{{ runStore.events.length }}</strong>
        <p>这里收纳所有关键事件，包括开始、完成、兜底与自动修复。</p>
      </div>

      <div v-if="deliveryVerificationSummary" class="glass-panel metric-card">
        <small>自动验证</small>
        <strong>{{ deliveryVerificationSummary.headline }}</strong>
        <p>{{ deliveryVerificationSummary.detail }}</p>
      </div>
    </div>

    <div class="glass-panel section-panel">
      <div class="section-heading">
        <div>
          <h3 class="card-title">系统执行轨迹</h3>
          <p class="helper-text">需要排查时再看这里；默认把它当作交付过程的内部轨迹即可。</p>
        </div>
        <span class="chip">阶段轨迹</span>
      </div>
      <StageBoard
        :current-stage="runStore.currentRun.current_stage"
        :workflow-code="runStore.currentRun.workflow_code"
      />
    </div>

    <div class="section-grid">
      <div class="span-5">
        <div class="glass-panel section-panel">
          <div class="section-heading">
            <div>
              <h3 class="card-title">任务上下文</h3>
              <p class="helper-text">这里保留原始需求、时间信息和错误信息，方便回顾输入背景。</p>
            </div>
            <span class="chip">本次概览</span>
          </div>

          <div class="list-stack">
            <div class="mini-card">
              <h4>需求输入</h4>
              <p>{{ runStore.currentRun.input_requirement }}</p>
            </div>
            <div class="mini-card">
              <h4>创建时间</h4>
              <p>{{ formatDateTime(runStore.currentRun.created_at) }}</p>
            </div>
            <div v-if="runStore.currentRun.error_message" class="mini-card timeline-card">
              <h4>错误信息</h4>
              <p>{{ runStore.currentRun.error_message }}</p>
            </div>
          </div>
        </div>
      </div>

      <div class="span-7">
        <div class="glass-panel table-card">
          <div class="section-heading">
            <div>
              <h3 class="card-title">验证与执行明细</h3>
              <p class="helper-text">先看自动验证结果；如果需要定位问题，再看下方阶段执行状态。</p>
            </div>
            <span class="chip">交付检查</span>
          </div>

          <div v-if="deliveryVerificationResults.length" class="list-stack" style="margin-bottom: 18px">
            <div
              v-for="result in deliveryVerificationResults"
              :key="`${result.label}-${result.command}`"
              class="mini-card"
            >
              <h4>{{ result.label }} · {{ result.success ? "通过" : "失败" }}</h4>
              <p>{{ result.summary }}</p>
              <div class="markdown-shell">
                <pre>{{ result.command }}</pre>
              </div>
            </div>
          </div>

          <div class="table-shell">
            <el-table :data="runStore.tasks" size="small">
              <el-table-column label="阶段" min-width="170">
                <template #default="{ row }">
                  {{ getStageLabel(row.step_code) }}
                </template>
              </el-table-column>
              <el-table-column label="负责角色" min-width="170">
                <template #default="{ row }">
                  {{ getAgentLabel(row.agent_code) }}
                </template>
              </el-table-column>
              <el-table-column label="状态" width="120">
                <template #default="{ row }">
                  <StatusTag :status="row.status" />
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </div>

      <div class="span-12">
        <div class="glass-panel section-panel">
          <div class="section-heading">
            <div>
              <h3 class="card-title">事件时间线</h3>
              <p class="helper-text">保留关键动态记录，适合排查为什么触发兜底、自动修复或失败。</p>
            </div>
            <span class="chip">动态记录</span>
          </div>
          <EventTimeline :events="runStore.events" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import axios from "axios";
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { downloadProjectPackage } from "../api/projects";
import EventTimeline from "../components/EventTimeline.vue";
import StageBoard from "../components/StageBoard.vue";
import StatusTag from "../components/StatusTag.vue";
import { getStoredAccessToken } from "../api/http";
import { useRunStore } from "../stores/run";
import type { DeliveryCommandSpec, DeliveryVerificationResult, RunEvent } from "../types";
import {
  asRecord,
  extractCommandSpecs,
  extractFirstStringList,
  extractVerificationResults,
  extractWorkspaceRoot,
} from "../utils/delivery";
import { extractFilenameFromDisposition, triggerBlobDownload } from "../utils/download";
import { getAgentLabel, getStageLabel, getStatusLabel } from "../utils/presentation";


const route = useRoute();
const router = useRouter();
const runStore = useRunStore();
const eventSource = ref<EventSource | null>(null);
const cancelling = ref(false);
const resuming = ref(false);
const downloadingPackage = ref(false);
const runUid = computed(() => String(route.params.runUid));
const projectUid = computed(() => {
  const value = route.query.projectUid;
  return typeof value === "string" ? value : "";
});
const canCancel = computed(() => {
  const status = runStore.currentRun?.status ?? "";
  return !["COMPLETED", "FAILED", "CANCELLED"].includes(status);
});
const canResume = computed(() => {
  const status = runStore.currentRun?.status ?? "";
  return ["FAILED", "CANCELLED"].includes(status);
});
const stateJson = computed(() => asRecord(runStore.currentRun?.state_json));
const deliveryHandoff = computed(() => asRecord(stateJson.value.delivery_handoff));
const deliveryIntegration = computed(() => asRecord(stateJson.value.integration_bundle));
const solutionPlan = computed(() => asRecord(stateJson.value.solution_delivery_plan));
const backendBundle = computed(() => asRecord(stateJson.value.backend_code_bundle));
const frontendBundle = computed(() => asRecord(stateJson.value.frontend_code_bundle));
const isDeliveryRun = computed(() => {
  return runStore.currentRun?.workflow_code === "delivery_v1" || Boolean(deliveryWorkspaceRoot.value);
});
const deliveryWorkspaceRoot = computed(() => {
  return extractWorkspaceRoot(deliveryHandoff.value) || extractWorkspaceRoot(deliveryIntegration.value);
});
const deliveryGeneratedAssets = computed(() => {
  const fromHandoff = extractFirstStringList(deliveryHandoff.value, ["generated_assets"]);
  if (fromHandoff.length) {
    return fromHandoff;
  }
  return extractFirstStringList(deliveryIntegration.value, ["generated_files"]);
});
const deliveryStartupGuide = computed(() => {
  const fromHandoff = extractFirstStringList(deliveryHandoff.value, ["startup_guide"]);
  if (fromHandoff.length) {
    return fromHandoff;
  }
  return extractFirstStringList(deliveryIntegration.value, ["startup_steps"]);
});
const deliveryNextSteps = computed(() => {
  const fromHandoff = extractFirstStringList(deliveryHandoff.value, ["next_steps", "verification_status"]);
  if (fromHandoff.length) {
    return fromHandoff;
  }
  return extractFirstStringList(deliveryIntegration.value, ["notes", "verification_steps"]);
});
const deliveryVerificationResults = computed<DeliveryVerificationResult[]>(() => {
  const fromHandoff = extractVerificationResults(deliveryHandoff.value.verification_results);
  if (fromHandoff.length) {
    return fromHandoff;
  }
  return extractVerificationResults(deliveryIntegration.value.verification_results);
});
const deliveryRunCommands = computed<DeliveryCommandSpec[]>(() => {
  const fromPlan = extractCommandSpecs(solutionPlan.value.run_commands);
  if (fromPlan.length) {
    return fromPlan;
  }
  return [
    ...extractCommandSpecs(backendBundle.value.run_commands),
    ...extractCommandSpecs(frontendBundle.value.run_commands),
  ];
});
const deliveryValidationCommands = computed<DeliveryCommandSpec[]>(() => {
  const fromPlan = extractCommandSpecs(solutionPlan.value.validation_commands);
  if (fromPlan.length) {
    return fromPlan;
  }

  return deliveryVerificationResults.value.map((item) => ({
    label: item.label,
    command: item.command,
    purpose: item.summary,
  }));
});
const fallbackCount = computed(() => runStore.events.filter((item) => item.event_type === "delivery.stage_fallback").length);
const repairCount = computed(() => runStore.events.filter((item) => item.event_type === "delivery.repair.completed").length);
const deliveryVerificationSummary = computed(() => {
  if (!deliveryVerificationResults.value.length) {
    return null;
  }

  const passed = deliveryVerificationResults.value.filter((item) => item.success).length;
  return {
    headline: passed === deliveryVerificationResults.value.length
      ? "全部通过"
      : `${passed}/${deliveryVerificationResults.value.length} 通过`,
    detail: deliveryVerificationResults.value
      .map((item) => `${item.label}${item.success ? "通过" : "失败"}`)
      .join("，"),
  };
});
const deliveryHeadline = computed(() => {
  const status = runStore.currentRun?.status ?? "";
  const currentStage = getStageLabel(runStore.currentRun?.current_stage ?? "created");

  if (status === "COMPLETED" && deliveryWorkspaceRoot.value) {
    return {
      title: "可运行交付已准备好",
      badge: "可以开始接收",
      description: "工作区、代码文件和自动验证结果都已经整理好，先看启动指南即可开始使用。",
    };
  }

  if (status === "FAILED") {
    return {
      title: "这次交付未完成",
      badge: "需要继续处理",
      description: "可以先看错误信息和事件时间线，再决定是继续执行还是修改需求后重跑。",
    };
  }

  if (status === "CANCELLED") {
    return {
      title: "这次交付已取消",
      badge: "已停止推进",
      description: "已有阶段结果仍然会保留，你可以从当前页面继续回看或重新发起执行。",
    };
  }

  return {
    title: `正在推进${currentStage}`,
    badge: "生成中",
    description: "系统会持续补充代码、验证结果和交付说明。当前页面会随着执行自动刷新。",
  };
});

onMounted(async () => {
  await refresh();
  connectStream();
});

onUnmounted(() => {
  eventSource.value?.close();
});

async function refresh() {
  await runStore.fetchRun(runUid.value);
}

function goArtifacts() {
  if (!projectUid.value) {
    return;
  }
  router.push(`/projects/${projectUid.value}/artifacts`);
}

async function handleDownloadPackage() {
  if (!projectUid.value) {
    return;
  }

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

async function handleCancel() {
  if (!runStore.currentRun) {
    return;
  }
  if (!canCancel.value) {
    ElMessage.info(`当前任务状态为“${getStatusLabel(runStore.currentRun.status)}”，不能再取消。`);
    return;
  }

  cancelling.value = true;
  try {
    const updated = await runStore.requestCancel(runUid.value);
    await refresh();
    if (updated.status === "CANCELLED") {
      ElMessage.success("已提交取消。当前阶段如果正在调用模型，会在收尾后停止后续阶段。");
      return;
    }
    ElMessage.info(`当前任务状态为“${getStatusLabel(updated.status)}”，不能再取消。`);
  } catch {
    ElMessage.error("取消失败，请稍后重试。");
  } finally {
    cancelling.value = false;
  }
}

async function handleResume() {
  if (!runStore.currentRun) {
    return;
  }
  if (!canResume.value) {
    ElMessage.info(`当前任务状态为“${getStatusLabel(runStore.currentRun.status)}”，不能继续执行。`);
    return;
  }

  resuming.value = true;
  try {
    await runStore.requestResume(runUid.value);
    await refresh();
    ElMessage.success("已重新发起执行。");
  } catch {
    ElMessage.error("继续执行失败，请稍后重试。");
  } finally {
    resuming.value = false;
  }
}

function connectStream() {
  const accessToken = getStoredAccessToken();
  if (!accessToken) {
    return;
  }

  eventSource.value?.close();
  eventSource.value = new EventSource(`/api/v1/runs/${runUid.value}/stream?access_token=${encodeURIComponent(accessToken)}`);
  eventSource.value.addEventListener("run.state", () => {
    refresh();
  });
  eventSource.value.addEventListener("run.event", (event) => {
    const parsed = JSON.parse((event as MessageEvent<string>).data) as RunEvent;
    runStore.appendEvent(parsed);
    if (
      parsed.event_type.includes("completed")
      || parsed.event_type.includes("failed")
      || parsed.event_type.includes("cancel")
    ) {
      refresh();
    }
  });
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString();
}
</script>
