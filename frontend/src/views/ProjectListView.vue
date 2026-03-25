<template>
  <div class="page">
    <section class="hero-banner">
      <div class="hero-panel">
        <p class="eyebrow">项目入口</p>
        <h2>把项目需求整理成清晰可读的设计成果</h2>
        <p class="hero-lead">
          在同一个工作台里录入项目背景、跟进任务进展，并集中查看需求、架构、前后端设计与测试方案。
        </p>

        <div class="hero-badges">
          <span class="chip">需求整理</span>
          <span class="chip">过程追踪</span>
          <span class="chip">成果归档</span>
        </div>
      </div>

      <div class="hero-stats">
        <div class="glass-panel metric-card metric-card--accent">
          <small>项目总数</small>
          <strong>{{ projectStore.projects.length }}</strong>
          <p>每个项目都保留自己的需求背景、任务记录和设计文档。</p>
        </div>

        <div class="glass-panel metric-card">
          <small>标准流程</small>
          <strong>技术设计</strong>
          <p>系统会按统一顺序生成需求、架构、前后端与测试方案。</p>
        </div>

        <div class="glass-panel metric-card">
          <small>进展同步</small>
          <strong>实时更新</strong>
          <p>运行过程中会持续更新阶段状态，方便跟进当前进度。</p>
        </div>

        <div class="glass-panel metric-card">
          <small>成果管理</small>
          <strong>集中归档</strong>
          <p>每次任务生成的设计文档都会保留下来，便于查看和复用。</p>
        </div>
      </div>
    </section>

    <div class="page-header">
      <div>
        <h2>项目空间</h2>
        <p>新建项目后，可以继续完善需求，并发起新的设计任务。</p>
      </div>
      <el-button type="primary" @click="dialogVisible = true">新建项目</el-button>
    </div>

    <div class="glass-panel section-panel">
      <div class="section-heading">
        <div>
          <h3 class="card-title">项目列表</h3>
          <p class="helper-text">这里展示当前工作台中的全部项目，点击卡片进入项目详情。</p>
        </div>
        <span class="chip">全部项目</span>
      </div>

      <div v-if="projectStore.projects.length" class="project-grid">
        <RouterLink
          v-for="project in projectStore.projects"
          :key="project.uid"
          :to="`/projects/${project.uid}`"
          class="project-card"
        >
          <h3>{{ project.name }}</h3>
          <p>{{ project.description || "当前还没有填写项目描述，可以进详情页继续完善。" }}</p>
          <div class="project-card__meta">
            <span>UID · {{ project.uid.slice(0, 10) }}</span>
            <span>更新于 {{ formatDate(project.updated_at) }}</span>
          </div>
        </RouterLink>
      </div>

      <div v-else class="mini-card empty-state">
        <h4>还没有项目</h4>
        <p>先创建第一个项目，把需求整理进去，再开始生成设计成果。</p>
      </div>
    </div>

    <el-dialog v-model="dialogVisible" title="新建项目" width="560px">
      <el-form :model="form" label-position="top" class="dialog-form">
        <el-form-item label="项目名称">
          <el-input v-model="form.name" placeholder="例如：SE-Agent Studio" />
        </el-form-item>
        <el-form-item label="项目描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="初始需求">
          <el-input v-model="form.latest_requirement" type="textarea" :rows="5" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">创建项目</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { RouterLink, useRouter } from "vue-router";

import { useProjectStore } from "../stores/project";


const router = useRouter();
const projectStore = useProjectStore();
const dialogVisible = ref(false);
const form = reactive({
  name: "",
  description: "",
  latest_requirement: "",
});

onMounted(() => {
  projectStore.fetchProjects();
});

async function handleCreate() {
  if (!form.name.trim()) {
    ElMessage.warning("请先填写项目名称。");
    return;
  }
  const project = await projectStore.create({ ...form });
  dialogVisible.value = false;
  Object.assign(form, { name: "", description: "", latest_requirement: "" });
  router.push(`/projects/${project.uid}`);
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString();
}
</script>
