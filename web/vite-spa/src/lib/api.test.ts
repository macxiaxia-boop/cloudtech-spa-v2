// @vitest-environment node
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { apiFetch, ApiError, setUnauthorizedHandler } from './api';

beforeEach(() => {
  vi.stubGlobal('sessionStorage', {
    getItem: (key: string) => {
      if (key === 'ct.auth.session') return 'test-only-signed-bearer';
      if (key === 'ct.auth.tenant_id') return 'tenant-a';
      return null;
    },
  });
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  setUnauthorizedHandler(() => {});
});

it('rejects external URLs, protocol-relative URLs and path traversal BEFORE any fetch', async () => {
  const mocked = vi.fn();
  vi.stubGlobal('fetch', mocked);
  for (const url of [
    'https://attacker.invalid/collect',
    'http://attacker.invalid/collect',
    '//attacker.invalid/collect',
    'javascript:alert(1)',
    '../saas/v1/me',
    '%2e%2e/saas/v1/me',
    'anything\\redirect',
  ]) {
    await expect(apiFetch(url)).rejects.toBeInstanceOf(ApiError);
  }
  expect(mocked).not.toHaveBeenCalled();
});

it('uses an internal relative API URL and keeps bearer tokens same-origin only', async () => {
  const mocked = vi.fn(async () => new Response(
    JSON.stringify({ result: 'real-json' }),
    { status: 200, headers: { 'content-type': 'application/json' } },
  ));
  vi.stubGlobal('fetch', mocked);
  const data = await apiFetch<{ result: string }>('workpaths/runs', {
    method: 'GET',
  });
  expect(data.result).toBe('real-json');
  expect(mocked).toHaveBeenCalledTimes(1);
  const [url, init] = mocked.mock.calls[0] as unknown as [string, RequestInit];
  expect(url).toBe('/api/v2/workpaths/runs');
  expect(init.redirect).toBe('error');
  expect((init.headers as Record<string, string>)['Authorization']).toBe('Bearer test-only-signed-bearer');
  expect(init.signal).toBeInstanceOf(AbortSignal);
});

it('actually aborts a pending request when the API timeout elapses', async () => {
  vi.useFakeTimers();
  let actualAbort = false;
  const mocked = vi.fn((_url: string, init: RequestInit) => new Promise<Response>((_resolve, reject) => {
    init.signal!.addEventListener('abort', () => {
      actualAbort = true;
      reject(new Error('AbortError'));
    }, { once: true });
  }));
  vi.stubGlobal('fetch', mocked);
  const pending = apiFetch('workpaths/runs', { method: 'POST', timeout: 100 });
  await vi.advanceTimersByTimeAsync(101);
  await expect(pending).rejects.toMatchObject({
    status: 0,
    statusText: 'Timeout',
  });
  expect(actualAbort).toBe(true);
  expect(mocked).toHaveBeenCalledTimes(1);
});

it('forwards external caller cancellation rather than falsely reporting timeout', async () => {
  const caller = new AbortController();
  vi.stubGlobal('fetch', vi.fn((_url: string, init: RequestInit) =>
    new Promise<Response>((_resolve, reject) => {
      init.signal!.addEventListener('abort', () => reject(new Error('cancelled by caller')));
    }),
  ));
  const pending = apiFetch('workpaths/runs', { signal: caller.signal });
  caller.abort();
  await expect(pending).rejects.toThrow('cancelled by caller');
});

it('preserves unauthorized rejection and clears the session through its handler', async () => {
  const handler = vi.fn();
  setUnauthorizedHandler(handler);
  vi.stubGlobal('fetch', vi.fn(async () => new Response('', { status: 401 })));
  await expect(apiFetch('workpaths/runs')).rejects.toMatchObject({
    status: 401,
    statusText: 'Unauthorized',
  });
  expect(handler).toHaveBeenCalledTimes(1);
});
