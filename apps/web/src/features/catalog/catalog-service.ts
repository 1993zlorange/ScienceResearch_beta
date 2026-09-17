import type { components } from '../../../../../packages/contracts/scienceresearch-api'

export type Catalog = components['schemas']['CatalogDTO']
export type CatalogArea = components['schemas']['CatalogAreaDTO']
export type CatalogWorkPackage = components['schemas']['WorkPackageDTO']
export type ResearchWorkflow = components['schemas']['ResearchWorkflowDTO']
export type ResearchWorkflowMap = components['schemas']['ResearchWorkflowMapDTO']

export async function fetchCatalog(signal?: AbortSignal): Promise<Catalog> {
  const response = await fetch('/api/v1/catalog', { credentials: 'same-origin', signal })
  if (!response.ok) {
    throw new Error(`目录加载失败（HTTP ${response.status}）`)
  }
  return (await response.json()) as Catalog
}

export async function fetchResearchWorkflowMap(signal?: AbortSignal): Promise<ResearchWorkflowMap> {
  const response = await fetch('/api/v1/research-workflow-map', { credentials: 'same-origin', signal })
  if (!response.ok) {
    throw new Error(`工作流地图加载失败（HTTP ${response.status}）`)
  }
  return (await response.json()) as ResearchWorkflowMap
}
