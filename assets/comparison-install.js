(() => {
  'use strict';
  const manifest = document.querySelector('link[rel="manifest"]');
  const dialog = document.getElementById('install-dialog');
  const native = document.getElementById('install-native');
  let installPrompt;
  document.querySelectorAll('[data-install-open]').forEach(button => {
    button.addEventListener('click', () => dialog?.showModal());
  });
  document.querySelectorAll('[data-install-close]').forEach(button => {
    button.addEventListener('click', () => dialog?.close());
  });
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    installPrompt = event;
    if (native) native.hidden = false;
  });
  native?.addEventListener('click', async () => {
    if (!installPrompt) return;
    await installPrompt.prompt();
    await installPrompt.userChoice;
    installPrompt = null;
    native.hidden = true;
  });
  const installed = () => {
    if (native) native.hidden = true;
    dialog?.close();
    document.querySelectorAll('[data-install-open]').forEach(button => { button.hidden = true; });
  };
  window.addEventListener('appinstalled', installed);
  if (navigator.standalone || matchMedia('(display-mode: standalone)').matches) installed();

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
