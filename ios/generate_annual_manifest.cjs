#!/usr/bin/env node
'use strict';

// Run against the exact copied app resources. No network or wall-clock fields.
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const crypto = require('node:crypto');
const digest = bytes => crypto.createHash('sha256').update(bytes).digest('hex');

function generateManifest(engineBytes, datasetBytes) {
  const engineModule = {exports: {}};
  // Execute the trusted build source in the same JS realm as its large JSON
  // input. Cross-realm property access substantially slows edition generation.
  const install = vm.runInThisContext('(function(module){\n' + engineBytes.toString('utf8') + '\n})',
    {filename: 'annual-portfolio-engine.js', timeout: 10000});
  install(engineModule);
  const engine = engineModule.exports;
  if (engine.VERSION !== 1 || typeof engine.datasetId !== 'function') throw new Error('Unsupported annual engine');
  const data = JSON.parse(datasetBytes.toString('utf8'));
  const manifest = {schemaVersion: 1, engineVersion: engine.VERSION,
    datasetId: engine.datasetId(data), engineSha256: digest(engineBytes), datasetSha256: digest(datasetBytes)};
  // A checksum detects accidental edits to the trusted build manifest itself.
  // App signing authenticates bundle resources; this is not a remote signature.
  manifest.manifestSha256 = digest(Buffer.from([manifest.schemaVersion, manifest.engineVersion, manifest.datasetId,
    manifest.engineSha256, manifest.datasetSha256, ''].join('\n'), 'utf8'));
  return manifest;
}

if (require.main === module) {
  const [enginePath, datasetPath, outputPath] = process.argv.slice(2);
  if (!enginePath || !datasetPath || !outputPath || process.argv.length !== 5) {
    throw new Error('Usage: node generate_annual_manifest.cjs <bundled-engine.js> <bundled-data.json> <output.json>');
  }
  const result = generateManifest(fs.readFileSync(enginePath), fs.readFileSync(datasetPath));
  fs.mkdirSync(path.dirname(outputPath), {recursive: true});
  fs.writeFileSync(outputPath, JSON.stringify(result) + '\n');
  process.stdout.write('Verified annual bundle manifest: ' + result.datasetId + '\n');
}
module.exports = {generateManifest};
