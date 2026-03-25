<template>
  <el-tag class="status-tag" :type="tagType" effect="dark" round>{{ statusLabel }}</el-tag>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { getStatusLabel } from "../utils/presentation";


const props = defineProps<{
  status: string;
}>();

const tagType = computed(() => {
  const mapping: Record<string, "success" | "warning" | "danger" | "info" | "primary"> = {
    COMPLETED: "success",
    SUCCEEDED: "success",
    RUNNING: "primary",
    QUEUED: "warning",
    CREATED: "warning",
    WAITING_REVIEW: "warning",
    RETRYING: "warning",
    FAILED: "danger",
    PARTIAL_FAILED: "danger",
    CANCELLED: "info",
    SKIPPED: "info",
  };
  return mapping[props.status] ?? "info";
});

const statusLabel = computed(() => getStatusLabel(props.status));
</script>
