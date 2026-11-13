import { describe, it, expect, vi, afterEach } from 'vitest'
import { request, ApiError } from '../../src/api/client'
afterEach(() => vi.unstubAllGlobals())
describe('local session errors', () => {
  it('notifies the login gate on expired sessions without exposing response input', async () => {
    const dispatch = vi.fn()
    vi.stubGlobal('window', { dispatchEvent: dispatch })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"code":"UNAUTHENTICATED"}', { status: 401 })))
    await expect(request('/session')).rejects.toBeInstanceOf(ApiError)
    expect(dispatch).toHaveBeenCalledOnce()
    expect(dispatch.mock.calls[0][0].type).toBe('commerce:unauthenticated')
  })
  it('does not mistake backend outage for an expired session', async () => {
    const dispatch = vi.fn(); vi.stubGlobal('window', { dispatchEvent: dispatch })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"code":"AUTH_BACKEND_UNAVAILABLE"}', { status: 503 })))
    await expect(request('/session')).rejects.toBeInstanceOf(ApiError)
    expect(dispatch).not.toHaveBeenCalled()
  })
})
