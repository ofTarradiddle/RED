/* Build substitutes a revision and an explicit public-file list. Scope: /compare/. */
'use strict';
const FILES = __APP_FILES__;
const PREFIX = 'hetzerk-compare-' + new URL(self.registration.scope).pathname + '-';
const CACHE = PREFIX + '__APP_REVISION__';
const ALLOWED = new Set(FILES.map(path => new URL(path, self.location.origin).href));

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await cache.addAll(FILES);
    await self.skipWaiting();
  })());
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    for (const name of await caches.keys()) {
      if (name.startsWith(PREFIX) && name !== CACHE) await caches.delete(name);
    }
    await self.clients.claim();
  })());
});
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET' || !ALLOWED.has(event.request.url)) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);
    try {
      const response = await fetch(event.request, {signal: controller.signal});
      if (!response.ok) throw new Error('Snapshot request failed');
      await cache.put(event.request, response.clone());
      return response;
    } catch (_) {
      const cached = await cache.match(event.request);
      if (!cached) return new Response('Offline. Reconnect to load this page.', {status: 503});
      const headers = new Headers(cached.headers);
      headers.set('X-Hetzerk-Cache', 'offline');
      return new Response(await cached.arrayBuffer(), {status: cached.status, headers});
    } finally {
      clearTimeout(timeout);
    }
  })());
});
