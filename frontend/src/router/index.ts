import { createRouter, createWebHistory } from "vue-router";

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
      path: "/:pathMatch(.*)*",
      name: "not-found",
      // Lazy-loaded: the 404 view is not needed for the initial landing render.
      component: () => import("@/views/NotFoundView.vue"),
    },
  ],
});

export default router;
