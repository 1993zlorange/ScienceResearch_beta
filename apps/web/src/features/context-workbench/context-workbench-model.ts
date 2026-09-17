import type {
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
} from './context-workbench-types'

export type {
  AchievementCard,
  Catalog,
  CatalogArea,
  Context,
  Progress,
  Workflow,
  WorkflowList,
  CatalogWorkPackage,
  ResearchWorkflow,
  ResearchWorkflowMap,
}

export type WorkbenchWorkflow = Omit<Workflow, 'achievement_cards'> & {
  achievement_cards: AchievementCard[]
}

export type WorkbenchStatus = 'complete' | 'has-cards' | 'not-started'

export interface WorkbenchItem {
  area: CatalogArea
  package: CatalogWorkPackage
  workflow: WorkbenchWorkflow
  status: WorkbenchStatus
  searchable: string
}

export interface WorkbenchFilters {
  area: string
  status: WorkbenchStatus | ''
  query: string
  important: boolean
}

export interface ContextWorkbenchSnapshot {
  context: Context
  workflowList: WorkflowList
}

const UNASSIGNED_AREA: CatalogArea = {
  id: 'UNASSIGNED',
  name: '未分配方面',
  work_packages: [],
}

export function workflowStatus(workflow: WorkbenchWorkflow): WorkbenchStatus {
  if (workflow.is_completed) return 'complete'
  return workflow.achievement_cards.length > 0 ? 'has-cards' : 'not-started'
}

export function workflowStatusLabel(status: WorkbenchStatus): string {
  return status === 'complete' ? '已完成' : status === 'has-cards' ? '有成效' : '未开始'
}

export function templateSearchValue(template: CatalogWorkPackage['template']): string {
  return JSON.stringify(template ?? {})
}

function workbenchItem(
  area: CatalogArea,
  packageValue: CatalogWorkPackage,
  workflow: WorkbenchWorkflow,
): WorkbenchItem {
  const normalizedWorkflow: WorkbenchWorkflow = {
    ...workflow,
    achievement_cards: workflow.achievement_cards,
  }
  const searchable = [
    packageValue.id,
    packageValue.name,
    packageValue.action,
    packageValue.deliverable,
    templateSearchValue(packageValue.template),
  ]
    .join(' ')
    .toLowerCase()

  return {
    area,
    package: packageValue,
    workflow: normalizedWorkflow,
    status: workflowStatus(normalizedWorkflow),
    searchable,
  }
}

export function buildWorkbenchItems(
  catalog: Catalog,
  workflows: readonly WorkbenchWorkflow[],
): { items: WorkbenchItem[]; unassigned: WorkbenchWorkflow[] } {
  const areaById = new Map(catalog.areas.map((area) => [area.id, area]))
  const packageById = new Map(
    catalog.areas.flatMap((area) => area.work_packages.map((packageValue) => [packageValue.id, packageValue] as const)),
  )
  const items: WorkbenchItem[] = []
  const unassigned: WorkbenchWorkflow[] = []

  for (const workflow of workflows) {
    const packageValue = packageById.get(workflow.work_package_id)
    const area = workflow.area_id ? areaById.get(workflow.area_id) : undefined
    if (!packageValue || !area) {
      unassigned.push({ ...workflow, achievement_cards: workflow.achievement_cards })
      continue
    }
    items.push(workbenchItem(area, packageValue, workflow))
  }

  items.sort((left, right) => {
    const areaDelta = catalog.areas.findIndex((area) => area.id === left.area.id) -
      catalog.areas.findIndex((area) => area.id === right.area.id)
    if (areaDelta !== 0) return areaDelta
    const leftPackageIndex = left.area.work_packages.findIndex((packageValue) => packageValue.id === left.package.id)
    const rightPackageIndex = right.area.work_packages.findIndex((packageValue) => packageValue.id === right.package.id)
    return leftPackageIndex - rightPackageIndex
  })

  return { items, unassigned }
}

export function matchesWorkbenchFilters(item: WorkbenchItem, filters: WorkbenchFilters): boolean {
  const query = filters.query.trim().toLowerCase()
  return (
    (!filters.area || item.area.name === filters.area) &&
    (!filters.status || item.status === filters.status) &&
    (!query || item.searchable.includes(query)) &&
    (!filters.important || item.workflow.achievement_cards.some((card) => card.is_important))
  )
}

export function filterWorkbenchItems(
  items: readonly WorkbenchItem[],
  filters: WorkbenchFilters,
): WorkbenchItem[] {
  return items.filter((item) => matchesWorkbenchFilters(item, filters))
}

export function selectedWorkPackageId(
  requested: unknown,
  items: readonly WorkbenchItem[],
): string | undefined {
  const value = typeof requested === 'string' ? requested : ''
  if (value && items.some((item) => item.package.id === value)) return value
  return items[0]?.package.id
}

export function visibleCardSummaries(
  items: readonly WorkbenchItem[],
  filters?: WorkbenchFilters,
): Array<{
  card: AchievementCard
  workPackageId: string
  workPackageName: string
}> {
  return items.flatMap((item) =>
    item.workflow.achievement_cards
      .filter((card) => !filters?.important || card.is_important)
      .map((card) => ({
        card,
        workPackageId: item.package.id,
        workPackageName: item.package.name,
      })),
  )
}



export function readRouteValue(value: unknown, fallback = ''): string {
  if (Array.isArray(value)) return readRouteValue(value[0], fallback)
  return typeof value === 'string' ? value : fallback
}

export const WORKBENCH_STATUS_VALUES = ['complete', 'has-cards', 'not-started'] as const

export interface WorkbenchUrlState {
  wp: string
  card: string
  directory: 'expanded' | 'collapsed'
  preview: string
  previewRail: '' | 'auto_compact' | 'user_expanded'
  view: 'packages' | 'workflows'
  workflow: string
}

export function readWorkbenchUrlState(query: Record<string, unknown>): WorkbenchUrlState {
  const directory = readRouteValue(query.directory)
  const previewRail = readRouteValue(query.preview_rail)
  const view = readRouteValue(query.view)
  return {
    wp: readRouteValue(query.wp),
    card: readRouteValue(query.card),
    directory: directory === 'collapsed' ? 'collapsed' : 'expanded',
    preview: readRouteValue(query.preview),
    previewRail: previewRail === 'auto_compact' || previewRail === 'user_expanded' ? previewRail : '',
    view: view === 'workflows' ? 'workflows' : 'packages',
    workflow: readRouteValue(query.workflow),
  }
}

export interface ResearchWorkflowViewItem {
  workflow: ResearchWorkflow
  items: WorkbenchItem[]
}

export function buildResearchWorkflowViewItems(
  workflowMap: ResearchWorkflowMap,
  items: readonly WorkbenchItem[],
): ResearchWorkflowViewItem[] {
  const itemByPackageId = new Map(items.map((item) => [item.package.id, item]))
  return workflowMap.workflows.map((workflow) => ({
    workflow,
    items: workflow.work_package_ids.flatMap((workPackageId) => {
      const item = itemByPackageId.get(workPackageId)
      return item ? [item] : []
    }),
  }))
}

export function selectedResearchWorkflowId(
  requested: unknown,
  workflowMap: ResearchWorkflowMap | null,
): string | undefined {
  const value = typeof requested === 'string' ? requested : ''
  if (value && workflowMap?.workflows.some((workflow) => workflow.id === value)) return value
  return workflowMap?.workflows[0]?.id
}

export function readWorkbenchFilters(query: Record<string, unknown>): WorkbenchFilters {
  const statusValue = readRouteValue(query.status)
  const status = WORKBENCH_STATUS_VALUES.find((value) => value === statusValue)
  return {
    area: readRouteValue(query.area),
    status: status ?? '',
    query: readRouteValue(query.query),
    important: readRouteValue(query.important) === 'true',
  }
}




