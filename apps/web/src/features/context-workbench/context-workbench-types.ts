import type {
  AchievementAttachment,
  AchievementCard,
  Context,
  Progress,
  Workflow,
  WorkflowList,
} from '../contexts/context-service'
import type {
  Catalog,
  CatalogArea,
  CatalogWorkPackage,
  ResearchWorkflow,
  ResearchWorkflowMap,
} from '../catalog/catalog-service'

export type {
  AchievementAttachment,
  AchievementCard,
  Catalog,
  CatalogArea,
  CatalogWorkPackage,
  ResearchWorkflow,
  ResearchWorkflowMap,
  Context,
  Progress,
  Workflow,
  WorkflowList,
}

export type WorkbenchWorkflow = Omit<Workflow, 'achievement_cards'> & {
  achievement_cards: AchievementCard[]
}

export interface ContextWorkbenchSnapshot {
  context: Context
  workflowList: WorkflowList
}
