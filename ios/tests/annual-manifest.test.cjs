'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {generateManifest} = require('../generate_annual_manifest.cjs');
const engine = require('../../assets/annual-portfolio-engine.js');
const engineBytes = fs.readFileSync(path.join(__dirname, '../../assets/annual-portfolio-engine.js'));
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
function fixture() {
  return {schema_version: 1, asOf: '2012-01-03', assets: [{id: 'A', points: [
    {date: '2011-01-03', adjustedClose: 100}, {date: '2012-01-03', adjustedClose: 110}]}],
    rounds: [{year: 2010, cutoff: '2010-12-31', executionDate: '2011-01-03', endDate: '2012-01-03',
      eligibleAssetIds: ['A'], valuationDates: ['2011-01-03', '2012-01-03']}]};
}
test('manifest preserves the ordinary edition and hashes exact bundle bytes deterministically', () => {
  const data = fixture(), bytes = Buffer.from(JSON.stringify(data) + '\n');
  const manifest = generateManifest(engineBytes, bytes);
  assert.deepEqual(generateManifest(engineBytes, bytes), manifest);
  assert.equal(manifest.datasetId, engine.datasetId(data));
  assert.equal(manifest.engineSha256, sha(engineBytes));
  assert.equal(manifest.datasetSha256, sha(bytes));
  assert.equal(manifest.manifestSha256, sha([1, 1, manifest.datasetId, manifest.engineSha256, manifest.datasetSha256, ''].join('\n')));
  const spaceOnly = generateManifest(engineBytes, Buffer.from(JSON.stringify(data, null, 2)));
  assert.equal(spaceOnly.datasetId, manifest.datasetId);
  assert.notEqual(spaceOnly.datasetSha256, manifest.datasetSha256);
  data.assets[0].points[1].adjustedClose = 111;
  const changed = generateManifest(engineBytes, Buffer.from(JSON.stringify(data)));
  assert.notEqual(changed.datasetId, manifest.datasetId);
  assert.notEqual(changed.manifestSha256, manifest.manifestSha256);
});
test('manifest generation still rejects invalid observed histories', () => {
  const data = fixture(); data.assets[0].points[1].adjustedClose = 0;
  assert.throws(() => generateManifest(engineBytes, Buffer.from(JSON.stringify(data))), /positive/);
});
