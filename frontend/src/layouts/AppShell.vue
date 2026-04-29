<template>
  <div class="app-shell">
    <aside class="sidebar">
      <RouterLink class="brand-lockup" to="/projects" aria-label="SE Agent Studio">
        <AppLogo class="brand-mark" />
        <span>
          <strong>SE Agent Studio</strong>
          <small>软件工程交付工作台</small>
        </span>
      </RouterLink>

      <div class="sidebar-overview">
        <div class="sidebar-stat">
          <span>当前流程</span>
          <strong>代码交付 v1</strong>
        </div>
        <div class="sidebar-stat">
          <span>交付资产</span>
          <strong>代码与验证</strong>
        </div>
      </div>

      <nav class="sidebar-nav">
        <RouterLink class="sidebar-link" to="/projects">项目空间</RouterLink>
        <RouterLink class="sidebar-link" to="/settings/llm">模型配置</RouterLink>
        <RouterLink class="sidebar-link" to="/admin">管理配置</RouterLink>
      </nav>

      <div class="sidebar-brief">
        <h4>交付闭环</h4>
        <p>需求、运行记录、代码产物和验证结果集中归档。</p>
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
      <header class="shell-header">
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
          <span class="shell-badge">{{ shellMeta.primaryBadge }}</span>
          <span class="shell-badge">{{ shellMeta.secondaryBadge }}</span>
        </div>
      </header>

      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import AppLogo from "../components/AppLogo.vue";
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
      title: "交付运行详情",
      description: "跟进阶段状态、异常信息、代码产物和自动验证结果。",
      primaryBadge: "阶段追踪",
      secondaryBadge: "验证结果",
    };
  }
  if (route.path.includes("/artifacts")) {
    return {
      kicker: "产物中心",
      title: "交付产物中心",
      description: "集中查看本项目沉淀的需求、方案、代码和验证资产。",
      primaryBadge: "成果归档",
      secondaryBadge: "代码资产",
    };
  }
  if (route.path.startsWith("/admin")) {
    return {
      kicker: "系统配置",
      title: "角色与流程模板",
      description: "查看当前平台启用的角色配置、默认模型和标准工作流。",
      primaryBadge: "角色模板",
      secondaryBadge: "工作流",
    };
  }
  if (route.path.startsWith("/settings/llm")) {
    return {
      kicker: "模型配置",
      title: "账号模型配置",
      description: "维护 API Key、接口地址、默认模型和角色独立配置。",
      primaryBadge: "账号级配置",
      secondaryBadge: "角色覆盖",
    };
  }
  if (route.path.startsWith("/projects/")) {
    return {
      kicker: "项目工作台",
      title: "项目交付工作台",
      description: "维护项目需求、发起代码交付运行，并回看历史记录。",
      primaryBadge: "需求输入",
      secondaryBadge: "运行历史",
    };
  }
  return {
    kicker: "项目总览",
    title: "项目空间",
    description: "管理项目、整理需求，并发起新的代码交付任务。",
    primaryBadge: "项目管理",
    secondaryBadge: "交付协作",
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
