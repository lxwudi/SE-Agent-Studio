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
import { getStageDescription } from "../utils/presentation";

defineProps<{
  currentStage?: string;
}>();

const steps = [
  { code: "requirements", title: "需求梳理", description: getStageDescription("requirements") },
  { code: "architecture", title: "架构设计", description: getStageDescription("architecture") },
  { code: "backend_design", title: "后端方案", description: getStageDescription("backend_design") },
  { code: "frontend_design", title: "前端方案", description: getStageDescription("frontend_design") },
  { code: "ai_design", title: "AI 集成", description: getStageDescription("ai_design") },
  { code: "quality_assurance", title: "测试方案", description: getStageDescription("quality_assurance") },
  { code: "consistency_review", title: "综合复核", description: getStageDescription("consistency_review") },
  { code: "completed", title: "已完成", description: getStageDescription("completed") },
];
</script>
