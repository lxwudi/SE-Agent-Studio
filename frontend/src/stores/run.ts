import { defineStore } from "pinia";
import { ref } from "vue";

import { cancelRun, createRun, getRun, listRunEvents, listRunTasks, resumeRun } from "../api/runs";
import type { FlowRun, RunEvent, TaskRun } from "../types";


export const useRunStore = defineStore("runStore", () => {
  const currentRun = ref<FlowRun | null>(null);
  const tasks = ref<TaskRun[]>([]);
  const events = ref<RunEvent[]>([]);
  const loading = ref(false);

  async function create(projectUid: string, requirementText: string) {
    const { data } = await createRun(projectUid, { requirement_text: requirementText });
    currentRun.value = data;
    return data;
  }

  async function fetchRun(runUid: string) {
    loading.value = true;
    try {
      const [runResponse, taskResponse, eventResponse] = await Promise.all([
        getRun(runUid),
        listRunTasks(runUid),
        listRunEvents(runUid),
      ]);
      currentRun.value = runResponse.data;
      tasks.value = taskResponse.data;
      events.value = eventResponse.data;
    } finally {
      loading.value = false;
    }
  }

  async function requestCancel(runUid: string) {
    const { data } = await cancelRun(runUid);
    currentRun.value = data;
  }

  async function requestResume(runUid: string) {
    const { data } = await resumeRun(runUid);
    currentRun.value = data;
  }

  function appendEvent(event: RunEvent) {
    if (!events.value.find((item) => item.id === event.id)) {
      events.value = [...events.value, event];
    }
  }

  return {
    currentRun,
    tasks,
    events,
    loading,
    create,
    fetchRun,
    requestCancel,
    requestResume,
    appendEvent,
  };
});

