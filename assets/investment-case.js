/* Accessible tabs with fully readable content when JavaScript is unavailable. */
document.querySelectorAll('[data-case-explorer]').forEach(explorer => {
  const list = explorer.querySelector('.case-tabs');
  const tabs = Array.from(list.querySelectorAll('button'));
  const panels = tabs.map(tab => document.getElementById(tab.getAttribute('aria-controls')));
  if (panels.some(panel => !panel)) return;

  function select(index, focus = false) {
    tabs.forEach((tab, i) => {
      const active = i === index;
      tab.setAttribute('aria-selected', String(active));
      tab.tabIndex = active ? 0 : -1;
      panels[i].hidden = !active;
    });
    if (focus) tabs[index].focus();
  }

  list.setAttribute('role', 'tablist');
  tabs.forEach((tab, index) => {
    tab.setAttribute('role', 'tab');
    panels[index].setAttribute('role', 'tabpanel');
    panels[index].tabIndex = 0;
    tab.addEventListener('click', () => select(index));
    tab.addEventListener('keydown', event => {
      let next;
      if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
      if (event.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length - 1;
      if (next === undefined) return;
      event.preventDefault();
      select(next, true);
    });
  });
  explorer.classList.add('is-enhanced');
  select(0);
});

// Source artwork opens as a plain image without JS, and in a zoomable dialog with JS.
(() => {
  const links = document.querySelectorAll('[data-case-visual]');
  if (!links.length || typeof HTMLDialogElement === 'undefined') return;
  const dialog = document.createElement('dialog');
  if (typeof dialog.showModal !== 'function') return;
  dialog.className = 'case-image-dialog';
  dialog.setAttribute('aria-labelledby', 'case-image-title');
  dialog.setAttribute('aria-describedby', 'case-image-caption');
  dialog.innerHTML = '<div class="case-image-toolbar"><h2 id="case-image-title"></h2><div><button type="button" class="case-image-zoom" aria-pressed="false">Zoom in</button><button type="button" class="case-image-close" autofocus>Close <span aria-hidden="true">×</span></button></div></div><div class="case-image-stage" tabindex="0" role="region" aria-label="Image viewer"><img alt=""></div><p id="case-image-caption"></p>';
  document.body.append(dialog);
  const title = dialog.querySelector('h2');
  const caption = dialog.querySelector('#case-image-caption');
  const stage = dialog.querySelector('.case-image-stage');
  const image = dialog.querySelector('img');
  const zoom = dialog.querySelector('.case-image-zoom');
  let opener;

  function resetZoom() {
    stage.classList.remove('is-zoomed');
    zoom.setAttribute('aria-pressed', 'false');
    zoom.textContent = 'Zoom in';
    stage.scrollTo(0, 0);
  }

  links.forEach(link => {
    link.setAttribute('aria-haspopup', 'dialog');
    link.addEventListener('click', event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      opener = link;
      const figure = link.closest('figure');
      const sourceImage = link.querySelector('img');
      title.textContent = figure.querySelector('.case-visual-meta strong').textContent;
      caption.textContent = figure.querySelector('figcaption p').textContent;
      image.src = link.href;
      image.alt = sourceImage.alt;
      image.style.setProperty('--case-source-width', `${sourceImage.getAttribute('width')}px`);
      resetZoom();
      dialog.showModal();
      document.documentElement.classList.add('case-image-open');
    });
  });
  zoom.addEventListener('click', () => {
    const enlarged = stage.classList.toggle('is-zoomed');
    zoom.setAttribute('aria-pressed', String(enlarged));
    zoom.textContent = enlarged ? 'Fit image' : 'Zoom in';
    if (!enlarged) stage.scrollTo(0, 0);
  });
  dialog.querySelector('.case-image-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    const bounds = dialog.getBoundingClientRect();
    if (event.target === dialog && (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom)) dialog.close();
  });
  dialog.addEventListener('close', () => {
    document.documentElement.classList.remove('case-image-open');
    opener?.focus({preventScroll: true});
  });
})();
