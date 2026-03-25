<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand-mark">SE</div>

      <div class="brand">
        <p class="eyebrow eyebrow--light">SE Agent Studio</p>
        <h1>软件工程多智能体工作台</h1>
        <p>把项目需求、设计过程与成果文档放进同一个清晰可追踪的协作空间。</p>
      </div>

      <div class="sidebar-overview">
        <div class="sidebar-stat">
          <span>当前流程</span>
          <strong>技术设计 v1</strong>
        </div>
        <div class="sidebar-stat">
          <span>成果形式</span>
          <strong>设计文档</strong>
        </div>
      </div>

      <nav class="sidebar-nav">
        <RouterLink class="sidebar-link" to="/projects">项目空间</RouterLink>
        <RouterLink class="sidebar-link" to="/settings/llm">模型配置</RouterLink>
        <RouterLink class="sidebar-link" to="/admin">管理配置</RouterLink>
      </nav>

      <div class="sidebar-brief">
        <p class="eyebrow eyebrow--light">工作台说明</p>
        <h4>项目需求到设计成果</h4>
        <p>在一个界面里查看项目需求、任务进展与设计文档，方便演示、沟通和回看。</p>
      </div>

      <div class="sidebar-profile" v-if="authStore.user">
        <div>
          <span>{{ authStore.user.display_name }}</span>
          <strong>{{ authStore.user.email }}</strong>
        </div>
        <button type="button" class="sidebar-profile__logout" @click="handleLogout">退出登录</button>
      </div>
    </aside>

    <main class="shell-main">
      <header class="shell-header glass-panel">
        <div>
          <p class="eyebrow">{{ shellMeta.kicker }}</p>
          <h2>{{ shellMeta.title }}</h2>
          <p>{{ shellMeta.description }}</p>
        </div>

        <div class="shell-badges">
          <span class="shell-badge">项目协作</span>
          <span class="shell-badge">进度可追踪</span>
          <span class="shell-badge">文档已归档</span>
        </div>
      </header>

      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { useAuthStore } from "../stores/auth";


const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const shellMeta = computed(() => {
  if (route.path.startsWith("/runs/")) {
    return {
      kicker: "运行进度",
      title: "查看设计任务的推进情况",
      description: "在这里跟进阶段状态、异常信息，以及最终生成的设计文档。",
    };
  }
  if (route.path.includes("/artifacts")) {
    return {
      kicker: "产物中心",
      title: "集中阅读本项目的设计文档",
      description: "把需求、架构、前后端设计、AI 方案和测试计划统一展示在这里。",
    };
  }
  if (route.path.startsWith("/admin")) {
    return {
      kicker: "系统配置",
      title: "查看角色与流程模板",
      description: "这里展示当前平台启用的角色配置和可用流程，便于统一管理。",
    };
  }
  if (route.path.startsWith("/settings/llm")) {
    return {
      kicker: "模型配置",
      title: "为当前账号接入自己的云端模型",
      description: "在这里保存你的 API Key、接口地址和默认模型，运行时会优先使用这套配置。",
    };
  }
  if (route.path.startsWith("/projects/")) {
    return {
      kicker: "项目工作台",
      title: "围绕单个项目推进设计任务",
      description: "补充项目需求，发起新的设计任务，并随时回看历史记录。",
    };
  }
  return {
    kicker: "项目总览",
    title: "从项目需求进入设计协作",
    description: "在这里创建项目、整理需求，并开始新的技术设计任务。",
  };
});

function handleLogout() {
  authStore.logout();
  router.push("/login");
}
</script>
