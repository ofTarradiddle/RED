#!/usr/bin/env node
'use strict';

// Run after building and serving the site. Requires Playwright and local Chrome.
// Usage: NODE_PATH=/path/to/node_modules node scripts/export_research_pdf.cjs
// Optional: RESEARCH_URL, CHROME_PATH, and RESEARCH_PDF_OUTPUT environment values.
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '..');
const url = process.env.RESEARCH_URL || 'http://127.0.0.1:8080/research/the-measure-of-fire.html';
const destination = path.resolve(process.env.RESEARCH_PDF_OUTPUT || path.join(root, 'assets/research/the-measure-of-fire.pdf'));
const chrome = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const temporary = destination.replace(/\.pdf$/i, '') + '.pending.pdf';
const markSvg = fs.readFileSync(path.join(root, 'assets/hetzerk-mark-still.svg'), 'utf8')
  .replace('viewBox="0 0 480 480"', 'viewBox="135 112 215 268"')
  .replace('<path ', '<path fill="#8b0000" ');
const markUrl = `data:image/svg+xml;base64,${Buffer.from(markSvg).toString('base64')}`;

async function main() {
  const browser = await chromium.launch({ headless: true, executablePath: chrome });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 1000 }, reducedMotion: 'reduce' });
    const failed = [];
    page.on('pageerror', error => failed.push(error.message));
    const response = await page.goto(url, { waitUntil: 'networkidle' });
    if (!response || !response.ok()) throw new Error(`Report unavailable: ${url} (${response && response.status()})`);
    await page.locator('body.report-page .report-body').waitFor();
    await page.evaluate(async () => {
      document.querySelectorAll('dialog[open]').forEach(dialog => dialog.close());
      // Use reliable print punctuation without changing the website's source copy.
      const textNodes = document.createTreeWalker(document.querySelector('main'), NodeFilter.SHOW_TEXT);
      while (textNodes.nextNode()) {
        textNodes.currentNode.nodeValue = textNodes.currentNode.nodeValue
          .replace(/\u2014/g, ' - ').replace(/[\u2010-\u2013]/g, '-');
      }
      document.querySelectorAll('img').forEach(image => { image.loading = 'eager'; });
      await document.fonts.ready;
      await Promise.all([...document.querySelectorAll('.report-hero img,.report-body img')].map(image => image.decode()));
    });
    await page.addStyleTag({ path: path.join(root, 'assets/research-print.css') });
    await page.emulateMedia({ media: 'print', reducedMotion: 'reduce' });
    const report = await page.locator('.report-body').innerText();
    for (const required of ['r-summary', 'r-rationale', 'r-process', 'r-evidence', 'r-why-now', 'r-durability', 'r-validation', 'r-sources']) {
      if (await page.locator(`#${required}`).count() !== 1) throw new Error(`Missing report section: ${required}`);
    }
    if (report.split(/\s+/).length < 1000) throw new Error('Report text is unexpectedly short.');
    if (failed.length) throw new Error(`Browser errors: ${failed.join('; ')}`);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    await page.pdf({
      path: temporary,
      format: 'A4',
      printBackground: true,
      preferCSSPageSize: true,
      tagged: true,
      outline: true,
      displayHeaderFooter: true,
      headerTemplate: `<div style="font-family:Arial,sans-serif;font-size:8px;width:100%;margin:0 68px;padding-bottom:5px;display:flex;align-items:center;justify-content:space-between;color:#766769"><span style="display:flex;align-items:center;color:#8b0000;font-weight:600;letter-spacing:1px"><img src="${markUrl}" alt="H" style="display:block;width:7px;height:9px;margin-right:1px">ETZERK ASSET MANAGEMENT</span><span>RESEARCH / INNOVATION FACTOR</span></div>`,
      footerTemplate: '<div style="font-family:Arial,sans-serif;font-size:8px;width:100%;margin:0 68px;padding-top:6px;border-top:1px solid #e5dcdc;display:flex;justify-content:space-between;color:#766769"><span>The Measure of Fire · Research report</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>'
    });
    fs.renameSync(temporary, destination);
    console.log(`Exported ${destination}`);
    console.log(`Source: ${url}`);
  } finally {
    await browser.close();
    if (fs.existsSync(temporary)) fs.unlinkSync(temporary);
  }
}

main().catch(error => { console.error(error.message); process.exitCode = 1; });
