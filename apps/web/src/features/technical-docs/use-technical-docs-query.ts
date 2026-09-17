import { useQuery } from '@tanstack/vue-query'
import { fetchTechnicalManualManifest } from './technical-docs-service'

export const technicalManualManifestQueryKey = ['technical-manual-manifest'] as const

export function useTechnicalManualManifestQuery() {
  return useQuery({
    queryKey: technicalManualManifestQueryKey,
    queryFn: ({ signal }) => fetchTechnicalManualManifest(signal),
    staleTime: 5 * 60_000,
    retry: 1,
  })
}
