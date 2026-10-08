// Authentication store: the authenticated user and session actions.
//
// This is genuine shared application state (justifying Pinia). It never stores
// tokens — the session lives in an HttpOnly cookie managed by the backend.

import { defineStore } from "pinia";
import { ref } from "vue";

import { apiGet, apiPost, ApiError } from "@/api/client";

export interface Me {
  id: string;
  display_name: string | null;
  github_username: string | null;
}

export const useAuthStore = defineStore("auth", () => {
  const me = ref<Me | null>(null);
  const loading = ref(false);
  const loaded = ref(false);

  const isAuthenticated = () => me.value !== null;

  // The login endpoint performs OAuth redirects, so navigate the whole page.
  function login(): void {
    window.location.assign("/api/auth/github/login");
  }

  async function fetchMe(): Promise<void> {
    loading.value = true;
    try {
      me.value = await apiGet<Me>("/api/me");
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        me.value = null;
      } else {
        throw error;
      }
    } finally {
      loading.value = false;
      loaded.value = true;
    }
  }

  async function logout(): Promise<void> {
    await apiPost("/api/auth/logout");
    me.value = null;
  }

  return { me, loading, loaded, isAuthenticated, login, fetchMe, logout };
});
