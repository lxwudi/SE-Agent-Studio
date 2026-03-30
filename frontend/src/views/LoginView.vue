<template>
  <div class="auth-page">
    <div class="login-card glass-panel">
      <div class="login-card__brand">
        <div class="brand-mark">SE</div>
        <div>
          <p class="eyebrow">SE Agent Studio</p>
          <h1>登录工作台</h1>
          <p>使用管理员账号进入项目空间、发起交付任务并查看代码产物。</p>
        </div>
      </div>

      <el-form class="dialog-form" label-position="top" @submit.prevent="handleLogin">
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="demo@se-agent.studio" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="输入登录密码" />
        </el-form-item>
        <el-button type="primary" :loading="submitting" @click="handleLogin">登录</el-button>
      </el-form>

      <p class="login-hint">首次启动时默认账号来自后端 `.env` 中的 `DEFAULT_OWNER_EMAIL` 与 `DEFAULT_OWNER_PASSWORD`。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "../stores/auth";


const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const submitting = ref(false);
const form = reactive({
  email: "demo@se-agent.studio",
  password: "ChangeMe123!",
});

async function handleLogin() {
  if (!form.email.trim() || !form.password.trim()) {
    ElMessage.warning("请填写邮箱和密码。");
    return;
  }

  submitting.value = true;
  try {
    await authStore.login(form);
    const redirect = typeof route.query.redirect === "string" ? route.query.redirect : "/projects";
    router.push(redirect);
  } catch (error) {
    ElMessage.error("登录失败，请检查邮箱或密码。");
    console.error(error);
  } finally {
    submitting.value = false;
  }
}
</script>
