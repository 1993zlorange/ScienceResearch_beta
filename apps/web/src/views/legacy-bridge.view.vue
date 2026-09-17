<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElAlert, ElButton } from 'element-plus'
import {
  isDownloadPath,
  legacyUrlFromPath,
  productPathFromUrl,
  safeLegacyUrl,
} from '../router/legacy-route'

const route = useRoute()
const router = useRouter()
const legacyRoot = ref<HTMLDivElement | null>(null)
const legacyMarkup = ref('')
const errorMessage = ref('')
const isLoading = ref(false)
let skipNextRouteLoad = false
let loadSequence = 0

function currentLegacyUrl(): URL | null {
  return legacyUrlFromPath(route.fullPath, window.location.origin)
}

function executeLegacyScripts(): void {
  const scripts = legacyRoot.value?.querySelectorAll('script') ?? []
  for (const script of scripts) {
    const executable = document.createElement('script')
    for (const attribute of script.attributes) {
      executable.setAttribute(attribute.name, attribute.value)
    }
    executable.textContent = script.textContent
    script.replaceWith(executable)
  }
}

function applyLegacyStyles(styles: Array<string | null>): void {
  for (const style of document.head.querySelectorAll('style[data-sr-legacy-style]')) {
    style.remove()
  }
  for (const css of styles) {
    const style = document.createElement('style')
    style.dataset.srLegacyStyle = 'true'
    style.textContent = css
    document.head.append(style)
  }
}

async function renderLegacyResponse(response: Response, navigateAfterRender = false): Promise<void> {
  if (!response.ok) {
    throw new Error(`页面加载失败（HTTP ${response.status}）`)
  }
  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.includes('text/html')) {
    window.location.assign(response.url)
    return
  }

  const documentNode = new DOMParser().parseFromString(await response.text(), 'text/html')
  const finalUrl = safeLegacyUrl(response.url, window.location.origin)
  if (!finalUrl) {
    throw new Error('兼容页面返回了非受控地址')
  }

  document.title = documentNode.title || '科研工作台'
  applyLegacyStyles([...documentNode.head.querySelectorAll('style')].map((style) => style.textContent))
  legacyMarkup.value = documentNode.body.innerHTML
  await nextTick()
  executeLegacyScripts()

  if (navigateAfterRender) {
    const targetPath = productPathFromUrl(finalUrl)
    if (targetPath !== route.fullPath) {
      skipNextRouteLoad = true
      await router.push(targetPath)
    }
  }
  window.scrollTo(0, 0)
}

async function loadLegacy(candidate: URL, navigateAfterRender = false): Promise<void> {
  const requestSequence = ++loadSequence
  isLoading.value = true
  errorMessage.value = ''
  try {
    const response = await fetch(candidate, { credentials: 'same-origin' })
    await renderLegacyResponse(response, navigateAfterRender)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '页面加载失败。'
  } finally {
    if (requestSequence === loadSequence) {
      isLoading.value = false
    }
  }
}

function download(url: URL): void {
  const anchor = document.createElement('a')
  anchor.href = url.href
  anchor.download = ''
  document.body.append(anchor)
  anchor.click()
  anchor.remove()
}

function handleLegacyClick(event: MouseEvent): void {
  const target = event.target instanceof Element ? event.target.closest<HTMLAnchorElement>('a[href]') : null
  if (
    !target ||
    event.defaultPrevented ||
    event.button !== 0 ||
    event.metaKey ||
    event.ctrlKey ||
    event.shiftKey ||
    event.altKey ||
    target.target ||
    target.hasAttribute('download')
  ) {
    return
  }

  const url = safeLegacyUrl(target.href, window.location.origin)
  if (!url) return

  event.preventDefault()
  if (isDownloadPath(url.pathname)) {
    download(url)
    return
  }
  void loadLegacy(url, true)
}

function requestUrl(form: HTMLFormElement, method: string, body: FormData): URL {
  const action = safeLegacyUrl(form.action, window.location.origin)
  if (!action) {
    throw new Error('拒绝提交到非同源地址')
  }
  if (method !== 'get') return action

  const url = new URL(action)
  for (const [key, value] of body.entries()) {
    if (typeof value === 'string') url.searchParams.append(key, value)
  }
  return url
}

function handleLegacySubmit(event: SubmitEvent): void {
  const form = event.target instanceof HTMLFormElement ? event.target : null
  if (!form || event.defaultPrevented) return

  event.preventDefault()
  const method = (form.method || 'get').toLowerCase()
  const body = new FormData(form)
  let url: URL
  try {
    url = requestUrl(form, method, body)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '提交失败。'
    return
  }

  const requestSequence = ++loadSequence
  isLoading.value = true
  errorMessage.value = ''
  void fetch(url, {
    method: method === 'get' ? 'GET' : method.toUpperCase(),
    body: method === 'get' ? undefined : body,
    credentials: 'same-origin',
  })
    .then((response) => renderLegacyResponse(response, true))
    .catch((error: unknown) => {
      errorMessage.value = error instanceof Error ? error.message : '提交失败。'
    })
    .finally(() => {
      if (requestSequence === loadSequence) {
        isLoading.value = false
      }
    })
}

function retry(): void {
  const candidate = currentLegacyUrl()
  if (candidate) void loadLegacy(candidate)
}

onMounted(() => {
  const candidate = currentLegacyUrl()
  if (candidate) void loadLegacy(candidate)
})

watch(
  () => route.fullPath,
  () => {
    if (skipNextRouteLoad) {
      skipNextRouteLoad = false
      return
    }
    const candidate = currentLegacyUrl()
    if (candidate) void loadLegacy(candidate)
  },
)
</script>

<template>
  <div class="legacy-bridge" data-runtime="vue-dom-script-bridge">
    <div v-if="isLoading && !legacyMarkup" class="bridge-loading" role="status">正在加载科研工作台…</div>
    <ElAlert
      v-if="errorMessage"
      class="bridge-error"
      type="error"
      show-icon
      :title="errorMessage"
      :closable="false"
      role="alert"
    >
      <ElButton type="primary" link :loading="isLoading" @click="retry">重试</ElButton>
    </ElAlert>
    <div
      ref="legacyRoot"
      class="legacy-document"
      @click.capture="handleLegacyClick"
      @submit.capture="handleLegacySubmit"
      v-html="legacyMarkup"
    ></div>
  </div>
</template>

