import { defineStore } from "pinia";
import { ref } from "vue";

import { createProject, getProject, listProjects } from "../api/projects";
import type { Project, ProjectDetail } from "../types";


export const useProjectStore = defineStore("projectStore", () => {
  const projects = ref<Project[]>([]);
  const currentProject = ref<ProjectDetail | null>(null);
  const loading = ref(false);

  async function fetchProjects() {
    loading.value = true;
    try {
      const { data } = await listProjects();
      projects.value = data;
    } finally {
      loading.value = false;
    }
  }

  async function fetchProject(projectUid: string) {
    loading.value = true;
    try {
      const { data } = await getProject(projectUid);
      currentProject.value = data;
    } finally {
      loading.value = false;
    }
  }

  async function create(payload: { name: string; description: string; latest_requirement: string }) {
    const { data } = await createProject(payload);
    projects.value = [data, ...projects.value];
    return data;
  }

  return {
    projects,
    currentProject,
    loading,
    fetchProjects,
    fetchProject,
    create,
  };
});

