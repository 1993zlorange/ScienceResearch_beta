export interface TechnicalManual {
  id: string
  title: string
  description: string
  source: string
  version: string
  url: string
  size_bytes: number
  sha256: string
}

export interface TechnicalManualManifest {
  version: string
  generated_at: string
  manuals: TechnicalManual[]
}

export async function fetchTechnicalManualManifest(signal?: AbortSignal): Promise<TechnicalManualManifest> {
  const response = await fetch('/generated/technical-docs/manifest.json', { credentials: 'same-origin', signal })
  if (!response.ok) {
    throw new Error(`技术说明清单加载失败（HTTP ${response.status}）`)
  }
  try {
    return (await response.json()) as TechnicalManualManifest
  } catch {
    throw new Error('技术说明清单格式无效')
  }
}
