import { computed, ref } from "vue";
import { defineStore } from "pinia";

import { getCurrentUser, login as loginRequest } from "../api/auth";
import {
  ACCESS_TOKEN_STORAGE_KEY,
  USER_STORAGE_KEY,
  clearStoredAccessToken,
  getStoredAccessToken,
  storeAccessToken,
} from "../api/http";
import type { AuthUser } from "../types";


function readStoredUser() {
  const raw = window.localStorage.getItem(USER_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    window.localStorage.removeItem(USER_STORAGE_KEY);
    return null;
  }
}


export const useAuthStore = defineStore("authStore", () => {
  const accessToken = ref<string | null>(getStoredAccessToken());
  const user = ref<AuthUser | null>(readStoredUser());
  const initialized = ref(false);
  const loading = ref(false);

  const isAuthenticated = computed(() => Boolean(accessToken.value && user.value));

  async function restoreSession() {
    if (!accessToken.value) {
      initialized.value = true;
      return;
    }

    loading.value = true;
    try {
      const { data } = await getCurrentUser();
      user.value = data;
      window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(data));
    } catch {
      logout();
    } finally {
      loading.value = false;
      initialized.value = true;
    }
  }

  async function login(payload: { email: string; password: string }) {
    const { data } = await loginRequest(payload);
    accessToken.value = data.access_token;
    user.value = data.user;
    storeAccessToken(data.access_token);
    window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(data.user));
  }

  function logout() {
    accessToken.value = null;
    user.value = null;
    clearStoredAccessToken();
    window.localStorage.removeItem(USER_STORAGE_KEY);
  }

  return {
    accessToken,
    user,
    initialized,
    loading,
    isAuthenticated,
    restoreSession,
    login,
    logout,
  };
});
