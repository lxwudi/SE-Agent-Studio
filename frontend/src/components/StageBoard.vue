<template>
  <div class="stage-board">
    <div
      v-for="(step, index) in steps"
      :key="step.code"
      class="stage-card"
      :class="{ 'is-active': step.code === currentStage }"
    >
      <span class="stage-card__index">{{ index + 1 }}</span>

      <div>
        <strong>{{ step.title }}</strong>
        <p>{{ step.description }}</p>
      </div>

      <el-tag size="small" :type="step.code === currentStage ? 'primary' : 'info'">
        {{ step.code === currentStage ? "当前阶段" : "等待/已过" }}
      </el-tag>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import { getStageDescription } from "../utils/presentation";

const props = defineProps<{
  currentStage?: string;
  workflowCode?: string;
}>();

const technicalSteps = [
  { code: "requirements", title: "需求梳理", description: getStageDescription("requirements") },
  { code: "architecture", title: "架构设计", description: getStageDescription("architecture") },
  { code: "backend_design", title: "后端方案", description: getStageDescription("backend_design") },
  { code: "frontend_design", title: "前端方案", description: getStageDescription("frontend_design") },
  { code: "ai_design", title: "AI 集成", description: getStageDescription("ai_design") },
  { code: "quality_assurance", title: "测试方案", description: getStageDescription("quality_assurance") },
  { code: "consistency_review", title: "综合复核", description: getStageDescription("consistency_review") },
  { code: "completed", title: "已完成", description: getStageDescription("completed") },
];

const deliverySteps = [
  { code: "delivery_requirements", title: "交付需求", description: getStageDescription("delivery_requirements") },
  { code: "solution_design", title: "实施方案", description: getStageDescription("solution_design") },
  { code: "backend_delivery", title: "后端交付", description: getStageDescription("backend_delivery") },
  { code: "frontend_delivery", title: "前端交付", description: getStageDescription("frontend_delivery") },
  { code: "integration", title: "集成交付", description: getStageDescription("integration") },
  { code: "handoff", title: "交付移交", description: getStageDescription("handoff") },
  { code: "completed", title: "已完成", description: getStageDescription("completed") },
];

const steps = computed(() => {
  if (props.workflowCode === "delivery_v1") {
    return deliverySteps;
  }
  if (props.currentStage && deliverySteps.some((step) => step.code === props.currentStage)) {
    return deliverySteps;
  }
  return technicalSteps;
});
</script>
