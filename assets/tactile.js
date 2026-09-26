/* Pointer lighting for tactile cards. All content and navigation work without it. */
(() => {
  'use strict';

  const start = () => {
    const surfaces = [...document.querySelectorAll('[data-tactile]')];
    if (!surfaces.length) return;

    const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const properties = ['--surface-x', '--surface-y', '--surface-rx', '--surface-ry'];
    const pending = new Map();
    const active = new Set();
    let frame = 0;

    const enabled = () => finePointer.matches && !reducedMotion.matches && !document.hidden;
    const clear = surface => properties.forEach(property => surface.style.removeProperty(property));
    const flush = () => {
      frame = 0;
      pending.forEach((position, surface) => {
        if (!position || !enabled()) {
          clear(surface);
          active.delete(surface);
          return;
        }
        const [x, y] = position;
        surface.style.setProperty('--surface-x', `${(x * 100).toFixed(1)}%`);
        surface.style.setProperty('--surface-y', `${(y * 100).toFixed(1)}%`);
        surface.style.setProperty('--surface-rx', `${((0.5 - y) * 2).toFixed(3)}deg`);
        surface.style.setProperty('--surface-ry', `${((x - 0.5) * 2).toFixed(3)}deg`);
      });
      pending.clear();
    };
    const queue = (surface, position) => {
      pending.set(surface, position);
      if (!frame) frame = window.requestAnimationFrame(flush);
    };
    const resetAll = () => {
      if (frame) window.cancelAnimationFrame(frame);
      frame = 0;
      pending.clear();
      active.forEach(clear);
      active.clear();
    };

    surfaces.forEach(surface => {
      const move = event => {
        if (!enabled() || event.pointerType === 'touch' || event.isPrimary === false) return;
        const bounds = surface.getBoundingClientRect();
        if (!bounds.width || !bounds.height) return;
        const clamp = value => Math.max(0, Math.min(1, value));
        active.add(surface);
        queue(surface, [
          clamp((event.clientX - bounds.left) / bounds.width),
          clamp((event.clientY - bounds.top) / bounds.height),
        ]);
      };
      const reset = () => queue(surface, null);
      surface.addEventListener('pointerenter', move, { passive: true });
      surface.addEventListener('pointermove', move, { passive: true });
      surface.addEventListener('pointerleave', reset, { passive: true });
      surface.addEventListener('pointercancel', reset, { passive: true });
      surface.addEventListener('blur', reset, true);
    });

    finePointer.addEventListener('change', resetAll);
    reducedMotion.addEventListener('change', resetAll);
    document.addEventListener('visibilitychange', resetAll);
    window.addEventListener('blur', resetAll);
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})();
