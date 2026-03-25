import { createRouter, createWebHistory } from "vue-router";

import AdminConfigView from "../views/AdminConfigView.vue";
import ArtifactCenterView from "../views/ArtifactCenterView.vue";
import LoginView from "../views/LoginView.vue";
import ProjectDetailView from "../views/ProjectDetailView.vue";
import ProjectListView from "../views/ProjectListView.vue";
import RunMonitorView from "../views/RunMonitorView.vue";
import { getStoredAccessToken } from "../api/http";


const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/projects" },
    { path: "/login", component: LoginView, meta: { guestOnly: true, noShell: true } },
    { path: "/projects", component: ProjectListView, meta: { requiresAuth: true } },
    { path: "/projects/:projectUid", component: ProjectDetailView, meta: { requiresAuth: true } },
    { path: "/projects/:projectUid/artifacts", component: ArtifactCenterView, meta: { requiresAuth: true } },
    { path: "/runs/:runUid", component: RunMonitorView, meta: { requiresAuth: true } },
    { path: "/admin", component: AdminConfigView, meta: { requiresAuth: true } },
  ],
});

router.beforeEach((to) => {
  const hasToken = Boolean(getStoredAccessToken());

  if (to.meta.requiresAuth && !hasToken) {
    return { path: "/login", query: { redirect: to.fullPath } };
  }

  if (to.meta.guestOnly && hasToken) {
    return "/projects";
  }

  return true;
});

export default router;
