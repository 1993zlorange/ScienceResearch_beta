import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import LegacyBridgeView from '../views/legacy-bridge.view.vue'

const WorkPackagesView = () => import('../views/work-packages.view.vue')
const ContextsView = () => import('../views/contexts.view.vue')
const ContextWorkbenchView = () => import('../views/context-workbench.view.vue')
const ContextDeleteView = () => import('../views/context-delete.view.vue')
const TechnicalDocsView = () => import('../views/technical-docs.view.vue')
const TechnicalManualView = () => import('../views/technical-manual.view.vue')

const routes: RouteRecordRaw[] = [
  {
    path: '/contexts',
    name: 'contexts',
    component: ContextsView,
    meta: { layout: 'home' },
  },
  {
    path: '/contexts/:contextId',
    name: 'context-workbench',
    component: ContextWorkbenchView,
    meta: { layout: 'home' },
  },
  {
    path: '/contexts/:contextId/delete',
    name: 'context-delete',
    component: ContextDeleteView,
  },
  {
    path: '/technical-docs',
    name: 'technical-docs',
    component: TechnicalDocsView,
    meta: { layout: 'home' },
  },
  {
    path: '/technical-docs/:manualId',
    name: 'technical-manual',
    component: TechnicalManualView,
    meta: { layout: 'home' },
  },
  {
    path: '/work-packages',
    name: 'work-packages',
    component: WorkPackagesView,
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'legacy-bridge',
    component: LegacyBridgeView,
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})



