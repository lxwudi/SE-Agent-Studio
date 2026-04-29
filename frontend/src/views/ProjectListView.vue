<template>
  <div class="page">
    <section class="workspace-overview">
      <div class="workspace-overview__content">
        <p class="eyebrow">项目空间</p>
        <h2>管理软件交付项目</h2>
        <p>为每个项目沉淀需求背景、运行记录、代码产物和验证结果。</p>
        <div class="workspace-overview__meta">
          <span class="chip">需求整理</span>
          <span class="chip">交付运行</span>
          <span class="chip">成果归档</span>
        </div>
      </div>

      <div class="workspace-overview__actions">
        <el-button type="primary" @click="dialogVisible = true">新建项目</el-button>
      </div>
    </section>

    <section class="metric-strip">
      <div class="glass-panel metric-card metric-card--accent">
        <small>项目总数</small>
        <strong>{{ projectStore.projects.length }}</strong>
        <p>当前工作台已创建的项目数量。</p>
      </div>

      <div class="glass-panel metric-card metric-card--teal">
        <small>标准流程</small>
        <strong>代码交付</strong>
        <p>从需求到代码、验证和交付总结。</p>
      </div>

      <div class="glass-panel metric-card metric-card--blue">
        <small>进度同步</small>
        <strong>实时更新</strong>
        <p>运行阶段和事件会持续记录。</p>
      </div>

      <div class="glass-panel metric-card">
        <small>成果管理</small>
        <strong>集中归档</strong>
        <p>代码包与验证结果统一保留。</p>
      </div>
    </section>

    <section class="glass-panel table-card">
      <div class="section-heading">
        <div>
          <h3 class="card-title">项目列表</h3>
          <p class="helper-text">点击项目进入详情页，继续完善需求或发起新的交付运行。</p>
        </div>
        <span class="chip">共 {{ projectStore.projects.length }} 个</span>
      </div>

      <div v-if="projectStore.projects.length" class="project-grid">
        <article
          v-for="project in projectStore.projects"
          :key="project.uid"
          class="project-card project-card--interactive"
          @click="goProject(project.uid)"
        >
          <div class="project-card__header">
            <span class="project-avatar">{{ getProjectInitial(project.name) }}</span>
            <div>
              <h3>{{ project.name }}</h3>
              <span class="status-pill">可继续交付</span>
            </div>
          </div>
          <p>{{ project.description || "当前还没有填写项目描述，可以进详情页继续完善。" }}</p>
          <div class="project-card__meta">
            <span>UID · {{ project.uid.slice(0, 10) }}</span>
            <span>更新于 {{ formatDate(project.updated_at) }}</span>
          </div>
          <div class="project-card__actions">
            <el-button @click.stop="goProject(project.uid)">进入项目</el-button>
            <el-button
              type="danger"
              plain
              :loading="deletingUid === project.uid"
              @click.stop="handleDelete(project.uid, project.name)"
            >
              删除项目
            </el-button>
          </div>
        </article>
      </div>

      <div v-else class="mini-card empty-state">
        <h4>还没有项目</h4>
        <p>先创建第一个项目，把需求整理进去，再开始生成可运行交付成果。</p>
      </div>
    </section>

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
import { ElMessage, ElMessageBox } from "element-plus";
import { useRouter } from "vue-router";

import { useProjectStore } from "../stores/project";


const router = useRouter();
const projectStore = useProjectStore();
const dialogVisible = ref(false);
const deletingUid = ref("");
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

function goProject(projectUid: string) {
  router.push(`/projects/${projectUid}`);
}

async function handleDelete(projectUid: string, projectName: string) {
  try {
    await ElMessageBox.confirm(
      `删除后，这个项目下的运行记录和产物也会一起移除。确认删除“${projectName}”吗？`,
      "删除项目",
      {
        type: "warning",
        confirmButtonText: "确认删除",
        cancelButtonText: "取消",
      },
    );
  } catch {
    return;
  }

  deletingUid.value = projectUid;
  try {
    await projectStore.remove(projectUid);
    ElMessage.success("项目已删除。");
  } catch {
    ElMessage.error("删除项目失败，请稍后重试。");
  } finally {
    deletingUid.value = "";
  }
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString();
}

function getProjectInitial(name: string) {
  const trimmed = name.trim();
  if (!trimmed) {
    return "SE";
  }
  const words = trimmed.split(/\s+/).filter(Boolean);
  if (words.length >= 2) {
    return words.slice(0, 2).map((word) => word[0]).join("").toUpperCase();
  }
  return trimmed.slice(0, 2).toUpperCase();
}
</script>
