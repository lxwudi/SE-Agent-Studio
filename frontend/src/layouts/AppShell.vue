<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand-mark">SE</div>

      <div class="brand">
        <p class="eyebrow eyebrow--light">SE Agent Studio</p>
        <h1>软件工程多智能体工作台</h1>
        <p>把项目需求、交付过程、代码产物和验证结果放进同一个清晰可追踪的协作空间。</p>
      </div>

      <div class="sidebar-overview">
        <div class="sidebar-stat">
          <span>默认流程</span>
          <strong>代码交付 v1</strong>
        </div>
        <div class="sidebar-stat">
          <span>成果形式</span>
          <strong>代码 + 验证</strong>
        </div>
      </div>

      <nav class="sidebar-nav">
        <RouterLink class="sidebar-link" to="/projects">项目空间</RouterLink>
        <RouterLink class="sidebar-link" to="/settings/llm">模型配置</RouterLink>
        <RouterLink class="sidebar-link" to="/admin">管理配置</RouterLink>
      </nav>

      <div class="sidebar-brief">
        <p class="eyebrow eyebrow--light">工作台说明</p>
        <h4>项目需求到可运行交付</h4>
        <p>在一个界面里查看项目需求、任务进展、最终代码和自动验证结果，方便演示、沟通和回看。</p>
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
          <div v-if="backMeta" class="shell-header__lead">
            <el-button class="shell-back-button" plain @click="handleBack">
              返回 {{ backMeta.label }}
            </el-button>
          </div>
          <p class="eyebrow">{{ shellMeta.kicker }}</p>
          <h2>{{ shellMeta.title }}</h2>
          <p>{{ shellMeta.description }}</p>
        </div>

        <div class="shell-badges">
          <span class="shell-badge">项目协作</span>
          <span class="shell-badge">进度可追踪</span>
          <span class="shell-badge">代码可交付</span>
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

const backMeta = computed(() => {
  const projectUid = typeof route.params.projectUid === "string" ? route.params.projectUid : "";
  const runProjectUid = typeof route.query.projectUid === "string" ? route.query.projectUid : "";

  if (route.path.includes("/artifacts")) {
    return {
      label: "项目工作台",
      target: projectUid ? `/projects/${projectUid}` : "/projects",
    };
  }
  if (route.path.startsWith("/runs/")) {
    return {
      label: runProjectUid ? "项目工作台" : "项目空间",
      target: runProjectUid ? `/projects/${runProjectUid}` : "/projects",
    };
  }
  if (route.path.startsWith("/projects/")) {
    return {
      label: "项目空间",
      target: "/projects",
    };
  }
  if (route.path.startsWith("/settings/llm") || route.path.startsWith("/admin")) {
    return {
      label: "项目空间",
      target: "/projects",
    };
  }
  return null;
});

const shellMeta = computed(() => {
  if (route.path.startsWith("/runs/")) {
    return {
      kicker: "运行进度",
      title: "查看交付任务的推进情况",
      description: "在这里跟进阶段状态、异常信息，以及最终生成的代码与验证结果。",
    };
  }
  if (route.path.includes("/artifacts")) {
    return {
      kicker: "产物中心",
      title: "集中查看本项目的交付产物",
      description: "把需求、方案、最终代码和自动验证结果统一展示在这里。",
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
      title: "围绕单个项目推进交付任务",
      description: "补充项目需求，发起新的代码交付运行，并随时回看历史记录。",
    };
  }
  return {
    kicker: "项目总览",
    title: "从项目需求进入交付协作",
    description: "在这里创建项目、整理需求，并开始新的代码交付任务。",
  };
});

function handleLogout() {
  authStore.logout();
  router.push("/login");
}

function handleBack() {
  if (!backMeta.value) {
    return;
  }
  router.push(backMeta.value.target);
}
</script>
