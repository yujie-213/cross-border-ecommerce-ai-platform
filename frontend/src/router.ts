import { ref } from 'vue'

/**
 * Minimal hash router: path segments + query string.
 * Refs are module-level so the whole app observes one source of truth
 * (URL is authoritative, which keeps back/forward/refresh working).
 */
export interface Route { path: string; segments: string[]; query: Record<string, string> }

function parse(hash: string): Route {
  const raw = hash.replace(/^#\/?/, '')
  const [pathPart, queryPart = ''] = raw.split('?')
  const path = '/' + pathPart.replace(/^\/|\/$/g, '')
  const query: Record<string, string> = {}
  new URLSearchParams(queryPart).forEach((value, key) => { if (value !== '') query[key] = value })
  return { path, segments: path.split('/').filter(Boolean), query }
}

export const route = ref<Route>(parse(typeof location === 'undefined' ? '' : location.hash))

export function startRouter() {
  const sync = () => { route.value = parse(location.hash) }
  window.addEventListener('hashchange', sync)
  sync()
  return () => window.removeEventListener('hashchange', sync)
}

export function href(path: string, query: Record<string, string | number | undefined> = {}) {
  const params = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => { if (value !== undefined && value !== '') params.set(key, String(value)) })
  const suffix = params.toString()
  return '#' + path + (suffix ? '?' + suffix : '')
}

export function navigate(path: string, query: Record<string, string | number | undefined> = {}) {
  const next = href(path, query)
  if (location.hash === next) return
  location.hash = next
}

/** Replaces only the listed keys, keeping the rest of the current query. */
export function setQuery(patch: Record<string, string | number | undefined>) {
  const merged: Record<string, string> = { ...route.value.query }
  Object.entries(patch).forEach(([key, value]) => {
    if (value === undefined || value === '') delete merged[key]
    else merged[key] = String(value)
  })
  navigate(route.value.path, merged)
}

export function back(fallback = '/suggestions') {
  if (history.length > 1) history.back()
  else navigate(fallback)
}
