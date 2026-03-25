<template>
  <div class="page">
    <div class="page-header">
      <div>
        <p class="eyebrow">系统配置</p>
        <h2>角色模板与工作流配置</h2>
        <p>这里集中展示当前启用的角色配置和可用流程，便于查看和统一管理。</p>
      </div>
      <div class="badge-row">
        <span class="chip">角色 {{ adminStore.agents.length }}</span>
        <span class="chip">流程 {{ adminStore.workflows.length }}</span>
        <el-button @click="adminStore.fetchConfig">刷新配置</el-button>
      </div>
    </div>

    <div class="section-grid">
      <div class="span-6">
        <div class="glass-panel table-card">
          <div class="section-heading">
            <div>
              <h3 class="card-title">角色模板</h3>
              <p class="helper-text">展示当前已接入平台的角色配置和默认模型。</p>
            </div>
            <span class="chip">角色列表</span>
          </div>

          <div class="table-shell">
            <el-table :data="adminStore.agents" size="small">
              <el-table-column prop="display_name" label="角色" min-width="150" />
              <el-table-column prop="agent_code" label="标识" min-width="160" />
              <el-table-column prop="default_model" label="模型" min-width="120" />
              <el-table-column label="启用" width="90">
                <template #default="{ row }">
                  <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? "是" : "否" }}</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </div>

      <div class="span-6">
        <div class="glass-panel table-card">
          <div class="section-heading">
            <div>
              <h3 class="card-title">工作流模板</h3>
              <p class="helper-text">展示当前可用的标准流程，便于直接发起设计任务。</p>
            </div>
            <span class="chip">流程列表</span>
          </div>

          <div class="table-shell">
            <el-table :data="adminStore.workflows" size="small">
              <el-table-column prop="name" label="名称" min-width="180" />
              <el-table-column prop="workflow_code" label="标识" min-width="160" />
              <el-table-column prop="version" label="版本" width="100" />
              <el-table-column label="启用" width="90">
                <template #default="{ row }">
                  <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? "是" : "否" }}</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from "vue";

import { useAdminConfigStore } from "../stores/admin";


const adminStore = useAdminConfigStore();

onMounted(() => {
  adminStore.fetchConfig();
});
</script>
