import { defineStore } from "pinia";
import { ref } from "vue";

import { listAgents, listWorkflows } from "../api/admin";
import type { AgentProfile, WorkflowTemplate } from "../types";


export const useAdminConfigStore = defineStore("adminConfigStore", () => {
  const agents = ref<AgentProfile[]>([]);
  const workflows = ref<WorkflowTemplate[]>([]);
  const loading = ref(false);

  async function fetchConfig() {
    loading.value = true;
    try {
      const [agentResponse, workflowResponse] = await Promise.all([listAgents(), listWorkflows()]);
      agents.value = agentResponse.data;
      workflows.value = workflowResponse.data;
    } finally {
      loading.value = false;
    }
  }

  return {
    agents,
    workflows,
    loading,
    fetchConfig,
  };
});

