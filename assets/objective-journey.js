/* Accessible objective chapters; every panel remains readable without JavaScript. */
(() => {
  'use strict';

  const start = () => {
    document.querySelectorAll('[data-objective-journey]').forEach(root => {
      if (root.classList.contains('is-enhanced')) return;
      const rail = root.querySelector('[data-objective-tabs]');
      const stage = root.querySelector('[data-objective-stage]');
      const tabs = [...root.querySelectorAll('[data-objective-tab]')];
      const panels = tabs.map(tab => document.getElementById(tab.getAttribute('aria-controls')));
      if (!rail || !stage || !tabs.length ||
          tabs.some(tab => tab.tagName !== 'BUTTON' || !rail.contains(tab)) ||
          panels.some(panel => !panel || !root.contains(panel) || !panel.matches('[data-objective-panel]')) ||
          new Set(panels).size !== panels.length) return;

      const previous = root.querySelector('[data-objective-prev]');
      const next = root.querySelector('[data-objective-next]');
      const count = root.querySelector('[data-objective-count]');
      const status = root.querySelector('[data-objective-status]');
      let active = 0;
      let initialized = false;
      let touch = null;

      const indexFromHash = hash => {
        if (!hash.startsWith('#')) return -1;
        let fragment = hash.slice(1);
        try { fragment = decodeURIComponent(fragment); } catch (_) { return -1; }
        return panels.findIndex(panel => panel.id === fragment);
      };
      const revealTab = tab => {
        const viewport = rail.getBoundingClientRect();
        const item = tab.getBoundingClientRect();
        const left = viewport.left + rail.clientLeft;
        const right = left + rail.clientWidth;
        let offset = rail.scrollLeft;
        if (item.left < left) offset += item.left - left;
        else if (item.right > right) offset += item.right - right;
        rail.scrollLeft = Math.max(0, Math.min(offset, rail.scrollWidth - rail.clientWidth));
      };
      const select = (index, focus = false) => {
        const target = Math.max(0, Math.min(index, tabs.length - 1));
        const changed = target !== active;
        const focusWouldHide = changed && panels[active].contains(document.activeElement);
        tabs.forEach((tab, i) => {
          tab.setAttribute('aria-selected', String(i === target));
          tab.tabIndex = i === target ? 0 : -1;
        });
        if (focus || focusWouldHide) tabs[target].focus({ preventScroll: true });
        panels.forEach((panel, i) => { panel.hidden = i !== target; });
        panels[target].querySelectorAll('img[loading="lazy"]').forEach(image => { image.loading = 'eager'; });
        active = target;
        root.dataset.active = String(active);
        if (previous) previous.disabled = active === 0;
        if (next) next.disabled = active === tabs.length - 1;
        if (count) count.textContent = `${String(active + 1).padStart(2, '0')} / ${String(tabs.length).padStart(2, '0')}`;
        if (status && initialized && changed) {
          const label = (tabs[active].querySelector('strong') || tabs[active]).textContent.trim();
          status.textContent = `Chapter ${active + 1} of ${tabs.length}: ${label}`;
        }
        revealTab(tabs[active]);
      };

      rail.setAttribute('role', 'tablist');
      tabs.forEach((tab, index) => {
        if (!tab.id) {
          let id = `${panels[index].id}-tab`;
          while (document.getElementById(id)) id += '-objective';
          tab.id = id;
        }
        tab.type = 'button';
        tab.setAttribute('role', 'tab');
        panels[index].setAttribute('role', 'tabpanel');
        panels[index].setAttribute('aria-labelledby', tab.id);
        if (!panels[index].hasAttribute('tabindex')) panels[index].tabIndex = 0;
        tab.addEventListener('click', () => select(index));
        tab.addEventListener('keydown', event => {
          if (event.altKey || event.ctrlKey || event.metaKey) return;
          let target;
          if (event.key === 'ArrowRight') target = (index + 1) % tabs.length;
          else if (event.key === 'ArrowLeft') target = (index - 1 + tabs.length) % tabs.length;
          else if (event.key === 'Home') target = 0;
          else if (event.key === 'End') target = tabs.length - 1;
          else return;
          event.preventDefault();
          select(target, true);
        });
      });
      if (previous) previous.addEventListener('click', () => select(active - 1));
      if (next) next.addEventListener('click', () => select(active + 1));

      // Explicit chapter links may live outside the component, such as a fund introduction.
      document.querySelectorAll('a[data-objective-select]').forEach(link => {
        if (indexFromHash(link.getAttribute('href') || '') < 0) return;
        link.addEventListener('click', event => {
          if (event.defaultPrevented || event.button !== 0 || event.altKey ||
              event.ctrlKey || event.metaKey || event.shiftKey) return;
          const target = indexFromHash(link.getAttribute('href') || '');
          if (target < 0) return;
          event.preventDefault();
          select(target);
          panels[target].focus({ preventScroll: true });
          panels[target].scrollIntoView({
            block: 'nearest',
            inline: 'nearest',
            behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth',
          });
        });
      });

      // Passive touch handling preserves native scrolling, links and form controls.
      stage.addEventListener('touchstart', event => {
        touch = null;
        if (event.touches.length !== 1 ||
            event.target.closest('a,button,input,select,textarea,summary,[contenteditable]')) return;
        const point = event.touches[0];
        touch = { id: point.identifier, x: point.clientX, y: point.clientY, chapter: active };
      }, { passive: true });
      stage.addEventListener('touchend', event => {
        const startPoint = touch;
        touch = null;
        if (!startPoint || event.touches.length || startPoint.chapter !== active) return;
        const point = [...event.changedTouches].find(item => item.identifier === startPoint.id);
        if (!point) return;
        const dx = point.clientX - startPoint.x;
        const dy = point.clientY - startPoint.y;
        if (Math.abs(dx) >= 60 && Math.abs(dx) > 1.5 * Math.abs(dy)) {
          select(active + (dx < 0 ? 1 : -1));
        }
      }, { passive: true });
      stage.addEventListener('touchcancel', () => { touch = null; }, { passive: true });

      select(Math.max(0, indexFromHash(window.location.hash)));
      initialized = true;
      root.classList.add('is-enhanced');

      // Prepare the original exhibits as their stage approaches the viewport.
      // Data-saving connections still load just the selected chapter.
      if ('IntersectionObserver' in window && !navigator.connection?.saveData) {
        const prepare = new IntersectionObserver(entries => {
          if (!entries.some(entry => entry.isIntersecting)) return;
          panels.forEach(panel => panel.querySelectorAll('img').forEach(image => { image.loading = 'eager'; }));
          prepare.disconnect();
        }, { rootMargin: '300px 0px' });
        prepare.observe(root);
      }
    });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})();
