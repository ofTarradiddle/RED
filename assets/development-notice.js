(() => {
  const notice = document.querySelector('[data-development-notice]');
  const close = notice?.querySelector('[data-development-notice-close]');
  if (!notice || !close) return;

  // A fresh browser session shows the notice again. Storage may be unavailable
  // in privacy modes; dismissing the current page must still work.
  const storageKey = 'hetzerk-development-notice-v1';
  try {
    if (sessionStorage.getItem(storageKey) === 'dismissed') {
      notice.hidden = true;
      return;
    }
  } catch (_) { /* Keep the notice visible when storage is unavailable. */ }

  close.hidden = false;
  close.addEventListener('click', () => {
    const moveFocus = document.activeElement === close;
    notice.hidden = true;
    try {
      sessionStorage.setItem(storageKey, 'dismissed');
    } catch (_) { /* Dismissal still works on this page. */ }
    if (moveFocus) {
      document.querySelector('header a[href], main a[href]')?.focus({ preventScroll: true });
    }
  });
})();
