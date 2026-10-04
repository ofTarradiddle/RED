(() => {
  'use strict';
  const manifest = document.querySelector('link[rel="manifest"]');
  const offline = document.getElementById('offline-status');
  const connectivity = () => { if (offline) offline.hidden = navigator.onLine; };
  window.addEventListener('online', connectivity);
  window.addEventListener('offline', connectivity);
  connectivity();
  if (manifest && 'serviceWorker' in navigator) {
    const workerURL = new URL('sw.js', manifest.href);
    navigator.serviceWorker.register(workerURL, {scope: new URL('./', workerURL).pathname})
      .catch(() => { /* Online comparison remains available if offline storage is blocked. */ });
  }
})();
