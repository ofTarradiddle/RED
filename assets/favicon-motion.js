/* Replay the original wing H as cached favicon frames; retain the SVG fallback. */
(() => {
  'use strict';
  const script = document.currentScript;
  const icon = document.querySelector('link[rel~="icon"]');
  if (!script || !icon || icon.dataset.motionReady || !window.ImageDecoder) return;
  icon.dataset.motionReady = 'true';
  const source = new URL('hetzerk-bounce.gif', script.src);
  const still = Object.fromEntries(['href', 'type', 'sizes'].map(key => [key, icon.getAttribute(key)]));
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let frames = [];
  let loading;
  let failed = false;
  let activePage = true;
  let animation = null;
  let epoch = 0;
  let lastFrame = -1;
  let cycle = 0;

  const allowed = () => activePage && !document.hidden && !motion.matches && !document.body?.classList.contains('ia-motion-paused') && !failed;
  const stop = () => {
    if (animation !== null) cancelAnimationFrame(animation);
    animation = null;
    lastFrame = -1;
    for (const [key, value] of Object.entries(still)) {
      if (value === null) icon.removeAttribute(key);
      else if (icon.getAttribute(key) !== value) icon.setAttribute(key, value);
    }
  };

  const prepare = () => loading ||= (async () => {
    let decoder;
    try {
      if (!await ImageDecoder.isTypeSupported('image/gif')) return;
      const response = await fetch(source);
      if (!response.ok) throw new Error('Logo animation unavailable');
      decoder = new ImageDecoder({data: await response.arrayBuffer(), type: 'image/gif'});
      await decoder.tracks.ready;
      const count = decoder.tracks.selectedTrack.frameCount;
      const canvas = document.createElement('canvas');
      canvas.width = canvas.height = 64;
      const context = canvas.getContext('2d');
      if (!context) return;
      // The source has 60 frames at 40 ms. Sample pairs without speeding up its bounce.
      for (let index = 0; index < count; index += 2) {
        const {image} = await decoder.decode({frameIndex: index});
        try {
          context.clearRect(0, 0, 64, 64);
          context.globalCompositeOperation = 'source-over';
          // Keep the full wing movement inside the cream tile at tab-icon scale.
          context.drawImage(image, -11.2, -8.5, 86.4, 86.4);
          context.globalCompositeOperation = 'source-in';
          context.fillStyle = '#8b0000';
          context.fillRect(0, 0, 64, 64);
          context.globalCompositeOperation = 'destination-over';
          context.fillStyle = '#fff8f5';
          context.beginPath();
          context.roundRect(0, 0, 64, 64, 10);
          context.fill();
          cycle += (image.duration || 40000) / 1000 * Math.min(2, count - index);
          frames.push({href: canvas.toDataURL('image/png'), end: cycle});
        } finally {
          image.close();
        }
      }
    } catch (_) {
      failed = true;
      frames = [];
      stop();
    } finally {
      if (decoder) decoder.close();
    }
  })();

  const tick = now => {
    if (!allowed()) { stop(); return; }
    const elapsed = (now - epoch) % cycle;
    const index = frames.findIndex(frame => elapsed < frame.end);
    if (index !== lastFrame) {
      icon.type = 'image/png';
      icon.sizes = '64x64';
      icon.href = frames[index].href;
      lastFrame = index;
    }
    animation = requestAnimationFrame(tick);
  };
  const sync = async () => {
    stop();
    if (!allowed()) return;
    await prepare();
    if (allowed() && frames.length > 1 && animation === null) {
      epoch = performance.now();
      tick(epoch);
    }
  };
  motion.addEventListener('change', sync);
  document.addEventListener('visibilitychange', sync);
  document.addEventListener('hetzerk:motion-change', sync);
  window.addEventListener('pagehide', () => { activePage = false; stop(); });
  window.addEventListener('pageshow', () => { activePage = true; sync(); });
  sync();
})();
