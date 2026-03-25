<template>
  <div class="page">
    <div class="page-header">
      <div>
        <p class="eyebrow">模型配置</p>
        <h2>为当前账号接入云端模型 API</h2>
        <p>保存后，系统会优先使用你自己的 OpenAI 兼容接口来运行多智能体流程。</p>
      </div>
      <div class="badge-row">
        <span class="chip">{{ config.is_ready ? "已就绪" : "未就绪" }}</span>
        <span class="chip">{{ config.enabled ? "已启用" : "未启用" }}</span>
        <el-button :loading="loading" @click="fetchConfig">刷新</el-button>
      </div>
    </div>

    <div class="section-grid">
      <div class="span-7">
        <div class="glass-panel table-card config-main-card">
          <div class="section-heading">
            <div>
              <h3 class="card-title">云端模型接入</h3>
              <p class="helper-text">支持 OpenAI 官方接口，也支持兼容 `OpenAI API` 的第三方云服务。</p>
            </div>
            <span class="chip">当前账号</span>
          </div>

          <el-form label-position="top" class="dialog-form" @submit.prevent="handleSave">
            <el-form-item label="服务名称">
              <el-input v-model="form.provider_name" placeholder="例如：OpenAI / Moonshot / DeepSeek 兼容接口" />
            </el-form-item>

            <el-form-item label="接口地址">
              <el-input v-model="form.base_url" placeholder="例如：https://api.openai.com/v1" />
            </el-form-item>

            <el-form-item label="默认模型">
              <el-input v-model="form.default_model" placeholder="例如：gpt-4.1-mini" />
            </el-form-item>

            <el-form-item label="API Key">
              <el-input
                v-model="form.api_key"
                type="password"
                show-password
                placeholder="留空则保持当前密钥不变"
              />
            </el-form-item>

            <div class="config-hint-row">
              <span>当前密钥：{{ config.has_api_key ? config.masked_api_key : "未配置" }}</span>
              <button type="button" class="link-button" @click="handleClearApiKey">清空当前密钥</button>
            </div>

            <div class="config-toggle-row">
              <div>
                <strong>启用当前配置</strong>
                <p>开启后，系统会优先使用你的账号配置来运行智能体。</p>
              </div>
              <el-switch v-model="form.enabled" />
            </div>

            <div class="config-actions">
              <el-button :loading="loading" @click="resetForm">重置</el-button>
              <el-button type="primary" :loading="saving" native-type="submit">保存配置</el-button>
            </div>
          </el-form>
        </div>
      </div>

      <div class="span-5">
        <div class="glass-panel table-card config-side-card">
          <div class="section-heading">
            <div>
              <h3 class="card-title">使用说明</h3>
              <p class="helper-text">配置完成后，项目运行会自动优先使用你的云端接口。</p>
            </div>
            <span class="chip">运行规则</span>
          </div>

          <div class="config-summary">
            <div class="summary-item">
              <span>当前状态</span>
              <strong>{{ config.is_ready ? "可以触发真实模型" : "还不能触发真实模型" }}</strong>
            </div>
            <div class="summary-item">
              <span>接口地址</span>
              <strong>{{ config.base_url || "未配置" }}</strong>
            </div>
            <div class="summary-item">
              <span>默认模型</span>
              <strong>{{ config.default_model || "未配置" }}</strong>
            </div>
            <div class="summary-item">
              <span>最近更新</span>
              <strong>{{ config.updated_at ? formatTime(config.updated_at) : "尚未保存" }}</strong>
            </div>
          </div>

          <div class="config-notes">
            <p>1. 当前页面保存的是“当前登录账号”的私有配置，不会直接写进项目代码仓库。</p>
            <p>2. 只要接口兼容 OpenAI 格式，这个产品就能直接接入。</p>
            <p>3. 如果接口不可用，运行会停在错误状态，你可以改完配置后重新发起任务。</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, reactive, ref } from "vue";

import { getLLMConfig, updateLLMConfig } from "../api/llmConfig";
import type { UserLLMConfig } from "../types";


const loading = ref(false);
const saving = ref(false);
const config = reactive<UserLLMConfig>({
  provider_name: "OpenAI Compatible",
  base_url: "https://api.openai.com/v1",
  default_model: "gpt-4.1-mini",
  enabled: false,
  has_api_key: false,
  masked_api_key: "",
  is_ready: false,
  updated_at: null,
});

const form = reactive({
  provider_name: "",
  base_url: "",
  default_model: "",
  api_key: "",
  enabled: false,
});

async function fetchConfig() {
  loading.value = true;
  try {
    const { data } = await getLLMConfig();
    applyConfig(data);
  } finally {
    loading.value = false;
  }
}

function applyConfig(data: UserLLMConfig) {
  Object.assign(config, data);
  form.provider_name = data.provider_name;
  form.base_url = data.base_url;
  form.default_model = data.default_model;
  form.api_key = "";
  form.enabled = data.enabled;
}

function resetForm() {
  form.provider_name = config.provider_name;
  form.base_url = config.base_url;
  form.default_model = config.default_model;
  form.api_key = "";
  form.enabled = config.enabled;
}

async function handleSave() {
  if (!form.base_url.trim()) {
    ElMessage.warning("请先填写接口地址。");
    return;
  }

  saving.value = true;
  try {
    const { data } = await updateLLMConfig({
      provider_name: form.provider_name,
      base_url: form.base_url,
      default_model: form.default_model,
      api_key: form.api_key || undefined,
      enabled: form.enabled,
    });
    applyConfig(data);
    ElMessage.success(data.is_ready ? "模型配置已保存，可以触发真实运行。" : "模型配置已保存。");
  } catch {
    ElMessage.error("保存失败，请检查接口地址或当前登录状态。");
  } finally {
    saving.value = false;
  }
}

async function handleClearApiKey() {
  saving.value = true;
  try {
    const { data } = await updateLLMConfig({
      clear_api_key: true,
      enabled: false,
    });
    applyConfig(data);
    ElMessage.success("当前密钥已清空。");
  } catch {
    ElMessage.error("清空失败，请稍后重试。");
  } finally {
    saving.value = false;
  }
}

function formatTime(value: string) {
  return new Date(value).toLocaleString();
}

onMounted(() => {
  fetchConfig();
});
</script>

<style scoped>
.config-hint-row,
.config-toggle-row,
.config-actions,
.config-summary {
  display: flex;
  gap: 16px;
}

.config-hint-row,
.config-toggle-row {
  align-items: center;
  justify-content: space-between;
}

.config-toggle-row {
  padding: 18px 20px;
  border: 1px solid rgba(116, 140, 171, 0.22);
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(255, 247, 238, 0.96), rgba(250, 242, 233, 0.92));
  margin-top: 8px;
}

.config-toggle-row strong {
  color: var(--text);
}

.config-toggle-row p {
  margin: 6px 0 0;
  color: var(--muted);
}

.config-actions {
  margin-top: 24px;
  justify-content: flex-end;
}

.config-summary {
  flex-direction: column;
  margin-top: 12px;
}

.config-side-card {
  background:
    radial-gradient(circle at top right, rgba(212, 166, 79, 0.12), transparent 34%),
    linear-gradient(180deg, rgba(255, 252, 247, 0.98), rgba(252, 246, 239, 0.94));
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px 18px;
  border-radius: 20px;
  border: 1px solid rgba(23, 37, 54, 0.08);
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 10px 24px rgba(23, 37, 54, 0.06);
}

.summary-item span {
  color: rgba(102, 117, 138, 0.92);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.summary-item strong {
  color: var(--text);
  font-size: 18px;
  line-height: 1.45;
  word-break: break-word;
}

.config-notes {
  margin-top: 22px;
  display: grid;
  gap: 12px;
  color: var(--muted);
}

.config-notes p {
  margin: 0;
  line-height: 1.75;
}

.link-button {
  border: none;
  background: transparent;
  color: #c85a30;
  font-weight: 700;
  cursor: pointer;
  padding: 0;
}
</style>
