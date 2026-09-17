export const LEGACY_BASE_PATH = '/_legacy'

export function isLegacyPath(pathname: string): boolean {
  return pathname === LEGACY_BASE_PATH || pathname.startsWith(`${LEGACY_BASE_PATH}/`)
}

export function safeLegacyUrl(candidate: string, origin: string): URL | null {
  try {
    const url = new URL(candidate, origin)
    return url.origin === origin && isLegacyPath(url.pathname) ? url : null
  } catch {
    return null
  }
}

export function legacyUrlFromPath(fullPath: string, origin: string): URL | null {
  const path = fullPath === '/' ? '' : fullPath
  return safeLegacyUrl(`${LEGACY_BASE_PATH}${path}`, origin)
}

export function productPathFromUrl(url: URL): string {
  const path = url.pathname === LEGACY_BASE_PATH ? '/' : url.pathname.slice(LEGACY_BASE_PATH.length) || '/'
  return `${path}${url.search}${url.hash}`
}

export function isDownloadPath(pathname: string): boolean {
  return /\/_legacy\/api\/achievement-attachments\/[^/]+$/.test(pathname)
}
