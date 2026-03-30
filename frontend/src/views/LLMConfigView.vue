<template>
  <div class="page">
    <div class="page-header">
      <div>
        <p class="eyebrow">模型配置</p>
        <h2>为账号和各个智能体设置独立模型</h2>
        <p>账号默认配置是全局兜底。每个智能体都可以再单独指定自己的服务名称、接口地址、API Key 和模型。</p>
      </div>
      <div class="badge-row">
        <span class="chip">{{ config.is_ready ? "账号默认已就绪" : "账号默认未就绪" }}</span>
        <span class="chip">角色独立配置 {{ activeRoleOverrideCount }}</span>
        <span class="chip">角色独立就绪 {{ readyRoleOverrideCount }}</span>
        <el-button :loading="loading" @click="fetchConfig">刷新</el-button>
      </div>
    </div>

    <div class="section-grid">
      <div class="span-7">
        <div class="glass-panel table-card config-main-card">
          <div class="section-heading">
            <div>
              <h3 class="card-title">账号默认配置</h3>
              <p class="helper-text">这套配置会作为所有智能体的默认兜底。角色没开独立配置时，就跟随这里运行。</p>
            </div>
            <span class="chip">账号级</span>
          </div>

          <el-form label-position="top" class="dialog-form" @submit.prevent="handleSave">
            <el-form-item label="服务名称">
              <el-input v-model="form.provider_name" placeholder="例如：OpenAI / Moonshot / DeepSeek" />
            </el-form-item>

            <el-form-item label="接口地址">
              <el-input v-model="form.base_url" placeholder="例如：https://api.openai.com/v1" />
            </el-form-item>

            <el-form-item label="账号默认模型">
              <el-select
                :model-value="form.default_model"
                filterable
                allow-create
                default-first-option
                clearable
                placeholder="优先从读取到的真实模型里选择"
                @update:model-value="setAccountDefaultModel"
                @clear="setAccountDefaultModel('')"
              >
                <el-option
                  v-for="option in accountModelSuggestions"
                  :key="`account-${option.model}`"
                  :label="`${option.model} · ${option.reason}`"
                  :value="option.model"
                />
              </el-select>
              <p class="field-helper">不知道怎么选时，可以先读取模型列表，或者点下面的一键推荐方案。</p>
              <div class="quick-model-row">
                <button
                  v-for="option in accountQuickSuggestions"
                  :key="`account-quick-${option.model}`"
                  type="button"
                  class="quick-model-pill"
                  @click="setAccountDefaultModel(option.model)"
                >
                  <strong>{{ option.model }}</strong>
                  <span>{{ option.reason }}</span>
                </button>
              </div>
            </el-form-item>

            <el-form-item label="API Key">
              <el-input
                v-model="form.api_key"
                type="password"
                show-password
                placeholder="留空则保持当前密钥不变"
              />
            </el-form-item>

            <div class="config-discovery-row">
              <div>
                <strong>读取账号可用模型</strong>
                <p>系统会用上面的地址和 API Key 访问 `/models`，读取成功后，下拉里会优先出现真实可用模型。</p>
              </div>
              <el-button :loading="discoveringAccount" plain @click="handleDiscoverAccountModels">读取模型列表</el-button>
            </div>

            <div v-if="accountDiscoveredModels.length" class="model-result-card">
              <p class="model-result-card__title">已读取到的账号可用模型</p>
              <div class="token-list">
                <el-tag
                  v-for="item in accountDiscoveredModels"
                  :key="`account-model-${item.model_id}`"
                  class="token-pill-tag"
                  effect="plain"
                >
                  {{ item.model_id }}
                </el-tag>
              </div>
            </div>

            <div class="config-hint-row">
              <span>当前密钥：{{ config.has_api_key ? config.masked_api_key : "未配置" }}</span>
              <button type="button" class="link-button" @click="handleClearApiKey">清空账号密钥</button>
            </div>

            <div class="config-toggle-row">
              <div>
                <strong>启用账号默认配置</strong>
                <p>关闭后，账号默认配置不会直接参与运行；只有你单独启用并配好的角色会继续工作。</p>
              </div>
              <el-switch v-model="form.enabled" />
            </div>

            <div class="config-starter-card">
              <div>
                <h4>不知道怎么填？先用推荐方案</h4>
                <p>{{ detectedAccountGuide.helper }}</p>
              </div>
              <div class="config-starter-card__actions">
                <span class="chip">{{ detectedAccountGuide.label }}</span>
                <el-button
                  v-if="hasRecommendedStarterPlan"
                  type="primary"
                  plain
                  @click="applyRecommendedPlan"
                >
                  一键填入推荐方案
                </el-button>
              </div>
              <div v-if="starterPlanRoleLabels.length" class="token-list">
                <el-tag
                  v-for="item in starterPlanRoleLabels"
                  :key="item"
                  class="token-pill-tag"
                  effect="plain"
                >
                  {{ item }}
                </el-tag>
              </div>
            </div>

            <div class="config-priority-card">
              <h4>运行时优先级</h4>
              <p>1. 角色独立配置中的模型 / URL / API Key</p>
              <p>2. 账号默认配置</p>
              <p>3. 角色模板默认模型</p>
              <p>4. 系统全局默认模型</p>
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
              <p class="helper-text">账号默认配置和角色独立配置可以混用，角色独立配置优先级更高。</p>
            </div>
            <span class="chip">运行规则</span>
          </div>

          <div class="config-summary">
            <div class="summary-item">
              <span>账号默认</span>
              <strong>{{ form.enabled ? "已启用" : "未启用" }}</strong>
            </div>
            <div class="summary-item">
              <span>账号默认模型</span>
              <strong>{{ form.default_model || "未设置" }}</strong>
            </div>
            <div class="summary-item">
              <span>角色独立配置</span>
              <strong>{{ activeRoleOverrideCount ? `${activeRoleOverrideCount} 个角色已独立配置` : "当前没有角色独立配置" }}</strong>
            </div>
            <div class="summary-item">
              <span>角色独立就绪</span>
              <strong>{{ readyRoleOverrideCount ? `${readyRoleOverrideCount} 个角色可以独立运行` : "当前没有独立可用角色" }}</strong>
            </div>
            <div class="summary-item">
              <span>最近更新</span>
              <strong>{{ config.updated_at ? formatTime(config.updated_at) : "尚未保存" }}</strong>
            </div>
          </div>

          <div class="config-notes">
            <p>1. 角色开启独立配置后，可以用完全不同的服务商、URL、API Key 和模型。</p>
            <p>2. 角色里留空的字段，会按顺序回退到账号默认配置。</p>
            <p>3. 如果账号默认关闭了，只有那些独立配置完整的角色还能继续运行。</p>
            <p>4. 你可以先保存密钥，再点“读取模型列表”，后面就不用反复手敲模型名了。</p>
          </div>
        </div>
      </div>
    </div>

    <div class="glass-panel table-card role-section">
      <div class="section-heading">
        <div>
          <h3 class="card-title">角色独立配置</h3>
          <p class="helper-text">这里的每张卡片都可以单独设置 provider、URL、API Key 和模型，真正按角色拆开运行。</p>
        </div>
        <span class="chip">角色 {{ config.available_roles.length }}</span>
      </div>

      <div class="role-model-grid">
        <div
          v-for="role in config.available_roles"
          :key="role.agent_code"
          class="role-model-card"
        >
          <div class="role-model-card__header">
            <div>
              <strong>{{ role.display_name }}</strong>
              <p>{{ role.agent_code }}</p>
            </div>
            <div class="role-tag-group">
              <el-tag :type="role.enabled ? 'success' : 'info'" effect="plain">
                {{ role.enabled ? "角色启用" : "角色停用" }}
              </el-tag>
              <el-tag :type="roleForms[role.agent_code]?.override_enabled ? 'warning' : 'info'" effect="plain">
                {{ roleForms[role.agent_code]?.override_enabled ? "独立配置" : "跟随账号" }}
              </el-tag>
            </div>
          </div>

          <p class="role-model-card__hint">角色模板默认模型：{{ role.role_default_model || "未设置" }}</p>
          <p class="role-model-card__effective">当前实际会使用：{{ getEffectiveRoleSummary(role) }}</p>

          <div class="config-toggle-row role-toggle-row">
            <div>
              <strong>启用角色独立配置</strong>
              <p>开启后，这个角色会优先使用自己卡片里的服务名称、URL、API Key 和模型。</p>
            </div>
            <el-switch v-model="roleForms[role.agent_code].override_enabled" />
          </div>

          <template v-if="roleForms[role.agent_code].override_enabled">
            <el-form label-position="top" class="dialog-form role-form">
              <el-form-item label="服务名称">
                <el-input
                  v-model="roleForms[role.agent_code].provider_name"
                  placeholder="留空则跟随账号默认服务名称"
                />
              </el-form-item>

              <el-form-item label="接口地址">
                <el-input
                  v-model="roleForms[role.agent_code].base_url"
                  placeholder="留空则跟随账号默认接口地址"
                />
              </el-form-item>

              <el-form-item label="角色专属模型">
                <el-select
                  :model-value="roleForms[role.agent_code].default_model"
                  filterable
                  allow-create
                  default-first-option
                  clearable
                  placeholder="优先从读取到的真实模型里选"
                  @update:model-value="onRoleModelChange(role.agent_code, $event)"
                  @clear="setRoleModel(role.agent_code, '')"
                >
                  <el-option
                    v-for="option in getRoleModelSuggestions(role)"
                    :key="`${role.agent_code}-${option.model}`"
                    :label="`${option.model} · ${option.reason}`"
                    :value="option.model"
                  />
                </el-select>
                <p class="field-helper">如果这里留空，运行时会回退到账号默认模型，再回退到角色模板默认模型。</p>
              </el-form-item>

              <div class="quick-model-row quick-model-row--compact">
                <button
                  type="button"
                  class="quick-model-pill quick-model-pill--ghost"
                  @click="setRoleModel(role.agent_code, '')"
                >
                  <strong>跟随账号默认模型</strong>
                  <span>{{ form.default_model || config.default_model || "未设置账号默认模型" }}</span>
                </button>
                <button
                  v-for="option in getRoleQuickSuggestions(role)"
                  :key="`${role.agent_code}-quick-${option.model}`"
                  type="button"
                  class="quick-model-pill"
                  @click="setRoleModel(role.agent_code, option.model)"
                >
                  <strong>{{ option.model }}</strong>
                  <span>{{ option.reason }}</span>
                </button>
              </div>

              <el-form-item label="角色专属 API Key">
                <el-input
                  v-model="roleForms[role.agent_code].api_key"
                  type="password"
                  show-password
                  placeholder="留空则保持当前密钥不变；如果还没配过，也会回退到账号默认 API Key"
                />
              </el-form-item>

              <div class="config-discovery-row role-discovery-row">
                <div>
                  <strong>读取这个角色可用的模型</strong>
                  <p>会优先用这个角色卡片里填写的 URL 和 API Key；如果你已经保存过密钥，也可以直接读取。</p>
                </div>
                <el-button
                  :loading="discoveringRoleCode === role.agent_code"
                  plain
                  @click="handleDiscoverRoleModels(role.agent_code)"
                >
                  读取模型列表
                </el-button>
              </div>

              <div v-if="roleDiscoveredModels[role.agent_code]?.length" class="model-result-card model-result-card--compact">
                <p class="model-result-card__title">这个角色可用的模型</p>
                <div class="token-list">
                  <el-tag
                    v-for="item in roleDiscoveredModels[role.agent_code]"
                    :key="`${role.agent_code}-${item.model_id}`"
                    class="token-pill-tag"
                    effect="plain"
                  >
                    {{ item.model_id }}
                  </el-tag>
                </div>
              </div>

              <div class="config-hint-row role-key-row">
                <span>当前角色密钥：{{ roleForms[role.agent_code].has_api_key ? roleForms[role.agent_code].masked_api_key : "未配置" }}</span>
                <button type="button" class="link-button" @click="markRoleApiKeyForClear(role.agent_code)">清空角色密钥</button>
              </div>
            </el-form>
          </template>

          <div v-else class="role-following-card">
            <p>当前跟随账号默认配置：</p>
            <p>服务名称：{{ form.provider_name || config.provider_name || "未设置" }}</p>
            <p>接口地址：{{ form.base_url || config.base_url || "未设置" }}</p>
            <p>模型：{{ form.default_model || config.default_model || role.role_default_model || "系统全局默认模型" }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";

import { discoverLLMModels, getLLMConfig, updateLLMConfig } from "../api/llmConfig";
import type { DiscoveredModelOption, UserLLMConfig } from "../types";

type ProviderKey = "openai" | "deepseek" | "moonshot" | "generic";

interface ModelSuggestion {
  model: string;
  reason: string;
}

interface ProviderModelGuide {
  key: ProviderKey;
  label: string;
  helper: string;
  suggestions: ModelSuggestion[];
  starterDefaultModel: string;
  starterRoleOverrides: Record<string, string>;
  roleRecommendations: Record<string, string[]>;
}

interface RoleFormState {
  override_enabled: boolean;
  provider_name: string;
  base_url: string;
  default_model: string;
  api_key: string;
  has_api_key: boolean;
  masked_api_key: string;
  clear_api_key: boolean;
}

const PROVIDER_MODEL_GUIDES: Record<ProviderKey, ProviderModelGuide> = {
  openai: {
    key: "openai",
    label: "OpenAI / GPT",
    helper: "如果你接的是 OpenAI，建议账号默认先用 gpt-4.1-mini；产品、架构和核心开发角色需要更强效果时，再单独切到 gpt-4.1。",
    suggestions: [
      { model: "gpt-4.1-mini", reason: "默认起步，成本稳" },
      { model: "gpt-4.1", reason: "复杂需求、架构和核心编码" },
      { model: "gpt-4o-mini", reason: "轻量任务更省" },
      { model: "gpt-4o", reason: "通用质量更高" },
      { model: "o4-mini", reason: "复杂推理更强" },
    ],
    starterDefaultModel: "gpt-4.1-mini",
    starterRoleOverrides: {
      product_manager: "gpt-4.1",
      software_architect: "gpt-4.1",
      backend_architect: "gpt-4.1",
      frontend_developer: "gpt-4.1",
    },
    roleRecommendations: {
      product_manager: ["gpt-4.1", "o4-mini", "gpt-4.1-mini"],
      software_architect: ["gpt-4.1", "o4-mini", "gpt-4.1-mini"],
      backend_architect: ["gpt-4.1", "gpt-4.1-mini", "o4-mini"],
      frontend_developer: ["gpt-4.1", "gpt-4.1-mini", "gpt-4o-mini"],
      api_tester: ["gpt-4.1-mini", "gpt-4o-mini", "gpt-4.1"],
      ai_engineer: ["gpt-4.1", "gpt-4.1-mini", "o4-mini"],
    },
  },
  deepseek: {
    key: "deepseek",
    label: "DeepSeek",
    helper: "如果你接的是 DeepSeek，账号默认推荐先用 deepseek-chat；产品和架构角色再按需切到 deepseek-reasoner。",
    suggestions: [
      { model: "deepseek-chat", reason: "通用编码与执行" },
      { model: "deepseek-reasoner", reason: "复杂推理、需求澄清和架构分析" },
    ],
    starterDefaultModel: "deepseek-chat",
    starterRoleOverrides: {
      product_manager: "deepseek-reasoner",
      software_architect: "deepseek-reasoner",
    },
    roleRecommendations: {
      product_manager: ["deepseek-reasoner", "deepseek-chat"],
      software_architect: ["deepseek-reasoner", "deepseek-chat"],
      backend_architect: ["deepseek-chat", "deepseek-reasoner"],
      frontend_developer: ["deepseek-chat", "deepseek-reasoner"],
      api_tester: ["deepseek-chat", "deepseek-reasoner"],
      ai_engineer: ["deepseek-chat", "deepseek-reasoner"],
    },
  },
  moonshot: {
    key: "moonshot",
    label: "Moonshot / Kimi",
    helper: "如果你接的是 Moonshot，建议账号默认先用 moonshot-v1-8k，需求和架构角色可以再切到 moonshot-v1-32k。",
    suggestions: [
      { model: "moonshot-v1-8k", reason: "默认起步，响应快" },
      { model: "moonshot-v1-32k", reason: "长上下文更稳" },
      { model: "moonshot-v1-128k", reason: "超长材料分析" },
    ],
    starterDefaultModel: "moonshot-v1-8k",
    starterRoleOverrides: {
      product_manager: "moonshot-v1-32k",
      software_architect: "moonshot-v1-32k",
    },
    roleRecommendations: {
      product_manager: ["moonshot-v1-32k", "moonshot-v1-8k"],
      software_architect: ["moonshot-v1-32k", "moonshot-v1-8k"],
      backend_architect: ["moonshot-v1-8k", "moonshot-v1-32k"],
      frontend_developer: ["moonshot-v1-8k", "moonshot-v1-32k"],
      api_tester: ["moonshot-v1-8k", "moonshot-v1-32k"],
      ai_engineer: ["moonshot-v1-8k", "moonshot-v1-32k"],
    },
  },
  generic: {
    key: "generic",
    label: "未识别服务商",
    helper: "暂时无法判断你的服务商支持哪些模型。先读取模型列表；如果服务商不支持列模型，再按服务商文档手动填。",
    suggestions: [],
    starterDefaultModel: "",
    starterRoleOverrides: {},
    roleRecommendations: {},
  },
};

const loading = ref(false);
const saving = ref(false);
const discoveringAccount = ref(false);
const discoveringRoleCode = ref("");

const config = reactive<UserLLMConfig>({
  provider_name: "OpenAI Compatible",
  base_url: "https://api.openai.com/v1",
  default_model: "gpt-4.1-mini",
  agent_model_overrides: {},
  available_roles: [],
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

const roleForms = reactive<Record<string, RoleFormState>>({});
const accountDiscoveredModels = ref<DiscoveredModelOption[]>([]);
const roleDiscoveredModels = reactive<Record<string, DiscoveredModelOption[]>>({});

const activeRoleOverrideCount = computed(() => {
  return Object.values(roleForms).filter((item) => item.override_enabled).length;
});

const readyRoleOverrideCount = computed(() => {
  return config.available_roles.filter((role) => isRoleReady(role.agent_code)).length;
});

const detectedAccountGuide = computed(() => {
  return resolveProviderGuide(form.provider_name, form.base_url, form.default_model);
});

const hasRecommendedStarterPlan = computed(() => {
  return Boolean(detectedAccountGuide.value.starterDefaultModel);
});

const accountModelSuggestions = computed(() => {
  return mergeModelSuggestions(
    accountDiscoveredModels.value.map((item) => ({
      model: item.model_id,
      reason: item.owned_by ? `服务商返回 · ${item.owned_by}` : "服务商返回的可用模型",
    })),
    detectedAccountGuide.value.suggestions,
    form.default_model ? [{ model: form.default_model, reason: "当前账号默认模型" }] : [],
    config.default_model ? [{ model: config.default_model, reason: "已保存的账号默认模型" }] : [],
  );
});

const accountQuickSuggestions = computed(() => {
  return accountModelSuggestions.value.slice(0, 3);
});

const starterPlanRoleLabels = computed(() => {
  return config.available_roles
    .filter((role) => Boolean(detectedAccountGuide.value.starterRoleOverrides[role.agent_code]))
    .map((role) => `${role.display_name} -> ${detectedAccountGuide.value.starterRoleOverrides[role.agent_code]}`);
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
  syncRoleForms(data);
  accountDiscoveredModels.value = [];
}

function resetForm() {
  form.provider_name = config.provider_name;
  form.base_url = config.base_url;
  form.default_model = config.default_model;
  form.api_key = "";
  form.enabled = config.enabled;
  syncRoleForms(config);
  accountDiscoveredModels.value = [];
}

function syncRoleForms(data: UserLLMConfig) {
  const nextCodes = new Set(data.available_roles.map((role) => role.agent_code));

  for (const code of Object.keys(roleForms)) {
    if (!nextCodes.has(code)) {
      delete roleForms[code];
    }
  }
  for (const code of Object.keys(roleDiscoveredModels)) {
    if (!nextCodes.has(code)) {
      delete roleDiscoveredModels[code];
    }
  }

  for (const role of data.available_roles) {
    roleForms[role.agent_code] = {
      override_enabled: role.override_enabled,
      provider_name: role.provider_name,
      base_url: role.base_url,
      default_model: role.default_model,
      api_key: "",
      has_api_key: role.has_api_key,
      masked_api_key: role.masked_api_key,
      clear_api_key: false,
    };
    roleDiscoveredModels[role.agent_code] = [];
  }
}

async function handleSave() {
  if (form.enabled && !form.base_url.trim()) {
    ElMessage.warning("启用账号默认配置时，请先填写账号接口地址。");
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
      agent_overrides: Object.fromEntries(
        config.available_roles.map((role) => {
          const roleForm = roleForms[role.agent_code];
          return [
            role.agent_code,
            {
              override_enabled: roleForm.override_enabled,
              provider_name: roleForm.provider_name.trim(),
              base_url: roleForm.base_url.trim(),
              default_model: roleForm.default_model.trim(),
              api_key: roleForm.api_key || undefined,
              clear_api_key: roleForm.clear_api_key,
            },
          ];
        }),
      ),
    });
    applyConfig(data);
    ElMessage.success("模型配置已保存。");
  } catch {
    ElMessage.error("保存失败，请检查接口地址、密钥或当前登录状态。");
  } finally {
    saving.value = false;
  }
}

async function handleClearApiKey() {
  saving.value = true;
  try {
    const { data } = await updateLLMConfig({
      clear_api_key: true,
      enabled: form.enabled,
    });
    applyConfig(data);
    ElMessage.success("账号密钥已清空。");
  } catch {
    ElMessage.error("清空失败，请稍后重试。");
  } finally {
    saving.value = false;
  }
}

function markRoleApiKeyForClear(agentCode: string) {
  const roleForm = roleForms[agentCode];
  roleForm.api_key = "";
  roleForm.has_api_key = false;
  roleForm.masked_api_key = "";
  roleForm.clear_api_key = true;
  ElMessage.success("已标记清空这个角色的密钥，保存配置后生效。");
}

async function handleDiscoverAccountModels() {
  discoveringAccount.value = true;
  try {
    const { data } = await discoverLLMModels({
      provider_name: form.provider_name,
      base_url: form.base_url,
      api_key: form.api_key || undefined,
    });
    accountDiscoveredModels.value = data.models;
    ElMessage.success(
      data.used_saved_api_key
        ? `已读取 ${data.models.length} 个模型，使用的是已保存的账号密钥。`
        : `已读取 ${data.models.length} 个模型。`,
    );
  } catch (error: any) {
    accountDiscoveredModels.value = [];
    ElMessage.error(error?.response?.data?.detail ?? "模型列表读取失败，请检查账号 URL 和密钥。");
  } finally {
    discoveringAccount.value = false;
  }
}

async function handleDiscoverRoleModels(agentCode: string) {
  const roleForm = roleForms[agentCode];
  discoveringRoleCode.value = agentCode;
  try {
    const { data } = await discoverLLMModels({
      agent_code: agentCode,
      provider_name: roleForm.provider_name || form.provider_name,
      base_url: roleForm.base_url || form.base_url,
      api_key: roleForm.api_key || undefined,
    });
    roleDiscoveredModels[agentCode] = data.models;
    ElMessage.success(
      data.used_saved_api_key
        ? `已读取 ${data.models.length} 个模型，使用的是这个角色已保存的密钥。`
        : `已读取 ${data.models.length} 个模型。`,
    );
  } catch (error: any) {
    roleDiscoveredModels[agentCode] = [];
    ElMessage.error(error?.response?.data?.detail ?? "角色模型列表读取失败，请检查 URL 和密钥。");
  } finally {
    discoveringRoleCode.value = "";
  }
}

function setAccountDefaultModel(value: string | undefined) {
  form.default_model = `${value ?? ""}`.trim();
}

function setRoleModel(agentCode: string, value: string | undefined) {
  roleForms[agentCode].default_model = `${value ?? ""}`.trim();
}

function onRoleModelChange(agentCode: string, value: string | undefined) {
  setRoleModel(agentCode, value);
}

function isRoleReady(agentCode: string) {
  const roleForm = roleForms[agentCode];
  if (!roleForm || !roleForm.override_enabled) {
    return false;
  }
  const effectiveBaseUrl = roleForm.base_url.trim() || (form.enabled ? form.base_url.trim() : "");
  const effectiveApiKey = roleForm.api_key.trim() || (roleForm.has_api_key ? "saved-role-key" : "") || (form.enabled && config.has_api_key ? "saved-account-key" : "");
  const effectiveModel = roleForm.default_model.trim() || (form.enabled ? form.default_model.trim() : "") || getRoleFallbackModel(agentCode);
  return Boolean(effectiveBaseUrl && effectiveApiKey && effectiveModel);
}

function getRoleFallbackModel(agentCode: string) {
  return config.available_roles.find((item) => item.agent_code === agentCode)?.role_default_model?.trim() || settingsFallbackModel();
}

function settingsFallbackModel() {
  return "系统全局默认模型";
}

function getEffectiveRoleSummary(role: UserLLMConfig["available_roles"][number]) {
  const roleForm = roleForms[role.agent_code];
  if (!roleForm) {
    return role.role_default_model || settingsFallbackModel();
  }

  const providerName = roleForm.override_enabled
    ? roleForm.provider_name.trim() || (form.enabled ? form.provider_name.trim() : "") || "账号默认服务"
    : form.provider_name.trim() || config.provider_name || "未设置服务";
  const baseUrl = roleForm.override_enabled
    ? roleForm.base_url.trim() || (form.enabled ? form.base_url.trim() : "") || "未设置地址"
    : form.base_url.trim() || config.base_url || "未设置地址";
  const model = roleForm.override_enabled
    ? roleForm.default_model.trim() || (form.enabled ? form.default_model.trim() : "") || role.role_default_model || settingsFallbackModel()
    : form.default_model.trim() || config.default_model || role.role_default_model || settingsFallbackModel();

  return `${providerName} / ${baseUrl} / ${model}`;
}

function resolveProviderGuide(providerName: string, baseUrl: string, defaultModel: string): ProviderModelGuide {
  const signal = `${providerName} ${baseUrl} ${defaultModel}`.toLowerCase();
  if (signal.includes("deepseek")) {
    return PROVIDER_MODEL_GUIDES.deepseek;
  }
  if (signal.includes("moonshot") || signal.includes("kimi")) {
    return PROVIDER_MODEL_GUIDES.moonshot;
  }
  if (signal.includes("openai") || signal.includes("gpt-") || signal.includes("o4-")) {
    return PROVIDER_MODEL_GUIDES.openai;
  }
  return PROVIDER_MODEL_GUIDES.generic;
}

function mergeModelSuggestions(...groups: ModelSuggestion[][]): ModelSuggestion[] {
  const merged: ModelSuggestion[] = [];
  const seen = new Set<string>();

  for (const group of groups) {
    for (const item of group) {
      const model = item.model.trim();
      if (!model || seen.has(model)) {
        continue;
      }
      seen.add(model);
      merged.push({ model, reason: item.reason });
    }
  }

  return merged;
}

function getRoleProviderGuide(role: UserLLMConfig["available_roles"][number]) {
  const roleForm = roleForms[role.agent_code];
  return resolveProviderGuide(
    roleForm?.provider_name || form.provider_name,
    roleForm?.base_url || form.base_url,
    roleForm?.default_model || form.default_model,
  );
}

function getRoleModelSuggestions(role: UserLLMConfig["available_roles"][number]) {
  const roleForm = roleForms[role.agent_code];
  const guide = getRoleProviderGuide(role);
  const discovered = (roleDiscoveredModels[role.agent_code] || accountDiscoveredModels.value).map((item) => ({
    model: item.model_id,
    reason: item.owned_by ? `服务商返回 · ${item.owned_by}` : "服务商返回的可用模型",
  }));
  const recommended = (guide.roleRecommendations[role.agent_code] || []).map((model) => ({ model, reason: "推荐给这个角色" }));
  const current = roleForm?.default_model ? [{ model: roleForm.default_model, reason: "当前角色模型" }] : [];
  const account = form.default_model ? [{ model: form.default_model, reason: "账号默认模型" }] : [];
  const fallback = role.role_default_model ? [{ model: role.role_default_model, reason: "角色模板默认模型" }] : [];
  return mergeModelSuggestions(current, discovered, recommended, guide.suggestions, account, fallback);
}

function getRoleQuickSuggestions(role: UserLLMConfig["available_roles"][number]) {
  return getRoleModelSuggestions(role).slice(0, 2);
}

function applyRecommendedPlan() {
  if (!detectedAccountGuide.value.starterDefaultModel) {
    ElMessage.warning("当前还没识别出服务商，暂时无法自动填推荐方案。");
    return;
  }

  form.default_model = detectedAccountGuide.value.starterDefaultModel;
  for (const role of config.available_roles) {
    if (!detectedAccountGuide.value.starterRoleOverrides[role.agent_code]) {
      continue;
    }
    roleForms[role.agent_code].override_enabled = true;
    roleForms[role.agent_code].default_model = detectedAccountGuide.value.starterRoleOverrides[role.agent_code];
  }
  ElMessage.success(`已按 ${detectedAccountGuide.value.label} 推荐方案填入角色模型。`);
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

.config-discovery-row,
.config-toggle-row {
  padding: 18px 20px;
  border: 1px solid rgba(116, 140, 171, 0.22);
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(255, 247, 238, 0.96), rgba(250, 242, 233, 0.92));
  margin-top: 8px;
}

.config-discovery-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.config-discovery-row strong,
.config-toggle-row strong {
  color: var(--text);
}

.config-discovery-row p,
.config-toggle-row p {
  margin: 6px 0 0;
  color: var(--muted);
}

.config-actions {
  margin-top: 24px;
  justify-content: flex-end;
}

.field-helper {
  margin: 10px 0 0;
  color: var(--muted);
  line-height: 1.65;
}

.quick-model-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  margin-top: 12px;
}

.quick-model-row--compact {
  grid-template-columns: 1fr;
}

.quick-model-pill {
  border: 1px solid rgba(23, 37, 54, 0.1);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.86);
  padding: 12px 14px;
  text-align: left;
  cursor: pointer;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.quick-model-pill:hover {
  transform: translateY(-1px);
  border-color: rgba(239, 107, 60, 0.32);
  box-shadow: 0 8px 18px rgba(23, 37, 54, 0.08);
}

.quick-model-pill strong {
  display: block;
  color: var(--text);
}

.quick-model-pill span {
  display: block;
  margin-top: 6px;
  color: var(--muted);
  line-height: 1.55;
}

.quick-model-pill--ghost {
  background: rgba(239, 107, 60, 0.08);
  border-color: rgba(239, 107, 60, 0.18);
}

.config-starter-card {
  margin-top: 18px;
  padding: 20px;
  border-radius: 22px;
  border: 1px solid rgba(239, 107, 60, 0.16);
  background:
    radial-gradient(circle at top right, rgba(239, 107, 60, 0.12), transparent 34%),
    rgba(255, 252, 247, 0.9);
}

.config-starter-card h4 {
  margin: 0;
  font-size: 18px;
}

.config-starter-card p {
  margin: 10px 0 0;
  color: var(--muted);
  line-height: 1.7;
}

.config-starter-card__actions {
  margin-top: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.token-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.token-pill-tag {
  margin: 0;
  border-radius: 999px;
  padding-inline: 2px;
}

.model-result-card {
  margin-top: 14px;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid rgba(23, 37, 54, 0.08);
  background: rgba(255, 255, 255, 0.74);
}

.model-result-card--compact {
  margin-top: 16px;
}

.model-result-card__title {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.config-priority-card {
  margin-top: 18px;
  padding: 18px 20px;
  border: 1px solid rgba(23, 37, 54, 0.08);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.72);
}

.config-priority-card h4 {
  margin: 0;
  font-size: 16px;
}

.config-priority-card p {
  margin: 10px 0 0;
  color: var(--muted);
  line-height: 1.65;
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

.role-section {
  margin-top: 26px;
}

.role-model-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  margin-top: 14px;
}

.role-model-card {
  padding: 20px;
  border-radius: 22px;
  border: 1px solid rgba(23, 37, 54, 0.08);
  background: rgba(255, 255, 255, 0.78);
}

.role-model-card__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.role-model-card__header strong {
  display: block;
  font-size: 18px;
}

.role-model-card__header p,
.role-model-card__hint {
  margin: 8px 0 0;
  color: var(--muted);
  line-height: 1.6;
}

.role-model-card__effective {
  margin: 10px 0 0;
  color: var(--text);
  font-weight: 700;
  line-height: 1.6;
  word-break: break-word;
}

.role-tag-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.role-toggle-row {
  margin-top: 16px;
}

.role-form {
  margin-top: 18px;
}

.role-discovery-row,
.role-key-row {
  margin-top: 14px;
}

.role-following-card {
  margin-top: 18px;
  padding: 16px 18px;
  border-radius: 18px;
  background: rgba(250, 244, 236, 0.9);
  border: 1px solid rgba(23, 37, 54, 0.08);
}

.role-following-card p {
  margin: 0 0 8px;
  color: var(--muted);
  line-height: 1.65;
}

@media (max-width: 900px) {
  .role-model-grid {
    grid-template-columns: 1fr;
  }

  .config-starter-card__actions,
  .config-discovery-row {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
