import { createRouter, createWebHistory } from "vue-router";

import { useAuthStore } from "@/stores/auth";
import LandingView from "@/views/LandingView.vue";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "landing",
      component: LandingView,
    },
    {
      path: "/admin",
      name: "admin",
      // Lazy-loaded. UX guard only; the backend enforces authorization.
      component: () => import("@/views/AdminView.vue"),
      meta: { requiresSuperadmin: true },
    },
    {
      path: "/:pathMatch(.*)*",
      name: "not-found",
      // Lazy-loaded: the 404 view is not needed for the initial landing render.
      component: () => import("@/views/NotFoundView.vue"),
    },
  ],
});

// Frontend route guard is a UX convenience only: it hides admin routes from
// non-admins. It is NOT a security boundary — the backend returns 401/403
// regardless of what the SPA renders.
router.beforeEach(async (to) => {
  if (!to.meta.requiresSuperadmin) {
    return true;
  }
  const auth = useAuthStore();
  if (!auth.loaded) {
    await auth.fetchMe();
  }
  if (!auth.isSuperadmin()) {
    return { name: "landing" };
  }
  return true;
});

export default router;
