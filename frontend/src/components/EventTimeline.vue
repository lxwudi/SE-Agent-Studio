<template>
  <el-timeline>
    <el-timeline-item
      v-for="event in events"
      :key="event.id"
      :timestamp="event.created_at"
      placement="top"
      :type="eventTypeColor(event.event_type)"
    >
      <div class="mini-card timeline-card">
        <div class="card-header">
          <h4>{{ getEventTypeLabel(event.event_type) }}</h4>
          <small>{{ getEventSourceLabel(event.event_source) }}</small>
        </div>
        <pre class="payload-block" style="margin-top: 12px">{{ formatPayload(event.payload_json) }}</pre>
      </div>
    </el-timeline-item>
  </el-timeline>
</template>

<script setup lang="ts">
import type { RunEvent } from "../types";
import { getEventSourceLabel, getEventTypeLabel } from "../utils/presentation";


defineProps<{
  events: RunEvent[];
}>();

function eventTypeColor(eventType: string) {
  const normalized = eventType.toLowerCase();
  if (normalized.includes("failed")) {
    return "danger";
  }
  if (normalized.includes("completed")) {
    return "success";
  }
  if (normalized.includes("started")) {
    return "primary";
  }
  return "info";
}

function formatPayload(payload: Record<string, unknown>) {
  return JSON.stringify(payload, null, 2);
}
</script>
