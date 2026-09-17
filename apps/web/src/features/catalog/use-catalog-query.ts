import { useQuery } from '@tanstack/vue-query'
import type { Ref } from 'vue'
import { fetchCatalog, fetchResearchWorkflowMap } from './catalog-service'

export const catalogQueryKey = ['catalog'] as const
export const researchWorkflowMapQueryKey = ['research-workflow-map'] as const

export function useCatalogQuery() {
  return useQuery({
    queryKey: catalogQueryKey,
    queryFn: ({ signal }) => fetchCatalog(signal),
    staleTime: 30_000,
    retry: 1,
  })
}

export function useResearchWorkflowMapQuery(options: { enabled?: Ref<boolean> } = {}) {
  return useQuery({
    queryKey: researchWorkflowMapQueryKey,
    queryFn: ({ signal }) => fetchResearchWorkflowMap(signal),
    enabled: options.enabled,
    staleTime: 30_000,
    retry: 1,
  })
}
