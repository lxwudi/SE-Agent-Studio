<template>
  <div class="page" v-if="runStore.currentRun">
    <div class="page-header">
      <div>
        <p class="eyebrow">运行进度</p>
        <h2>{{ runStore.currentRun.run_uid }}</h2>
        <p>集中查看本次设计任务的阶段推进、执行记录和异常信息。</p>
      </div>

      <div class="badge-row">
        <StatusTag :status="runStore.currentRun.status" />
        <el-button @click="refresh">刷新状态</el-button>
        <el-button type="warning" :loading="resuming" :disabled="!canResume" @click="handleResume">继续执行</el-button>
        <el-button type="danger" plain :loading="cancelling" :disabled="!canCancel" @click="handleCancel">取消任务</el-button>
      </div>
    </div>

    <div class="run-summary-grid">
      <div class="glass-panel metric-card metric-card--accent">
        <small>当前阶段</small>
        <strong>{{ getStageLabel(runStore.currentRun.current_stage) }}</strong>
        <p>系统会持续更新当前所处阶段，便于随时掌握进度。</p>
      </div>

      <div class="glass-panel metric-card">
        <small>执行步骤</small>
        <strong>{{ runStore.tasks.length }}</strong>
        <p>每个阶段都会留下执行情况和结果，方便回看全过程。</p>
      </div>

      <div class="glass-panel metric-card">
        <small>动态更新</small>
        <strong>{{ runStore.events.length }}</strong>
        <p>这里保留任务中的重要过程记录，包括开始、完成和异常。</p>
      </div>
    </div>

    <div class="glass-panel section-panel">
      <div class="section-heading">
        <div>
          <h3 class="card-title">流程进度</h3>
          <p class="helper-text">按照技术设计任务的顺序展示当前推进情况。</p>
        </div>
        <span class="chip">阶段轨迹</span>
      </div>
      <StageBoard :current-stage="runStore.currentRun.current_stage" />
    </div>

    <div class="section-grid">
      <div class="span-5">
        <div class="glass-panel section-panel">
          <div class="section-heading">
            <div>
              <h3 class="card-title">任务摘要</h3>
              <p class="helper-text">这里汇总本次任务的核心输入和异常信息。</p>
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
              <h3 class="card-title">执行记录</h3>
              <p class="helper-text">按阶段查看本次任务由谁执行，目前状态如何。</p>
            </div>
            <span class="chip">阶段明细</span>
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
              <p class="helper-text">记录任务开始、完成和异常等关键过程，方便快速回看。</p>
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
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute } from "vue-router";

import EventTimeline from "../components/EventTimeline.vue";
import StageBoard from "../components/StageBoard.vue";
import StatusTag from "../components/StatusTag.vue";
import { getStoredAccessToken } from "../api/http";
import { useRunStore } from "../stores/run";
import type { RunEvent } from "../types";
import { getAgentLabel, getStageLabel, getStatusLabel } from "../utils/presentation";


const route = useRoute();
const runStore = useRunStore();
const eventSource = ref<EventSource | null>(null);
const cancelling = ref(false);
const resuming = ref(false);
const runUid = computed(() => String(route.params.runUid));
const canCancel = computed(() => {
  const status = runStore.currentRun?.status ?? "";
  return !["COMPLETED", "FAILED", "CANCELLED"].includes(status);
});
const canResume = computed(() => {
  const status = runStore.currentRun?.status ?? "";
  return ["FAILED", "CANCELLED"].includes(status);
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
