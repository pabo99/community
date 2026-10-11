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
      // Administration workspace. All admin screens share the AdminLayout shell
      // (left sidebar). UX guard only; the backend enforces authorization.
      path: "/admin",
      // Lazy-loaded: the admin shell is not needed for the initial landing render.
      component: () => import("@/layouts/AdminLayout.vue"),
      meta: { requiresSuperadmin: true },
      children: [
        {
          path: "",
          name: "admin",
          component: () => import("@/views/AdminView.vue"),
        },
        {
          path: "programs",
          name: "admin-programs",
          component: () => import("@/views/admin/ProgramsListView.vue"),
        },
        {
          path: "programs/:programId",
          name: "admin-program-detail",
          component: () => import("@/views/admin/ProgramDetailView.vue"),
        },
        {
          path: "editions/:editionId",
          name: "admin-edition-detail",
          component: () => import("@/views/admin/EditionDetailView.vue"),
        },
      ],
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
// regardless of what the SPA renders. The guard checks the matched records so
// the meta flag set on the parent `/admin` route protects every child.
router.beforeEach(async (to) => {
  if (!to.matched.some((record) => record.meta.requiresSuperadmin)) {
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
