'use strict';
(() => {
  const dialog = document.getElementById('disclaimerOverlay');
  if (!dialog) return;
  const storageKey = 'researchDisclaimerAgreed';
  let agreed = false;
  try { agreed = sessionStorage.getItem(storageKey) === 'true'; } catch (_) {}

  if (agreed) {
    dialog.removeAttribute('open');
    return;
  }

  dialog.querySelector('form[method="dialog"]').addEventListener('submit', () => {
    // Storage may be unavailable in private/restricted browsers. Native form
    // submission must still close the dialog after the visitor clicks Agree.
    try { sessionStorage.setItem(storageKey, 'true'); } catch (_) {}
  });
  dialog.addEventListener('close', () => {
    document.documentElement.classList.remove('research-agreement-open');
    if (dialog.returnValue === 'agree') {
      const heading = document.querySelector('h1');
      if (heading) {
        heading.tabIndex = -1;
        heading.focus({preventScroll: true});
      }
    }
  });
  dialog.addEventListener('cancel', event => {
    event.preventDefault();
    // The generated link includes the GitHub Pages repository prefix.
    location.assign(dialog.querySelector('[data-research-cancel]').href);
  });
  if (typeof dialog.showModal === 'function') {
    dialog.removeAttribute('open');
    dialog.showModal();
    document.documentElement.classList.add('research-agreement-open');
  }
})();
