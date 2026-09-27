# Optional public innovation-game leaderboard

This service is implemented but **not deployed or connected to the site**. The static site can keep a browser-local leaderboard without it. A shared board needs a Cloudflare account, a Worker and a D1 database; GitHub Pages cannot accept and persist score submissions itself.

The Worker imports the exact game engine used by the browser. It fetches an operator-configured dataset over HTTPS, verifies its SHA-256 digest, and replays submitted decisions using the standard $100 rules. It never accepts a client-supplied ending balance, starting capital, price history or ranking. Entries are separated by the engine's canonical dataset ID. D1 persists scores across deploys; identical decision replays deduplicate even if someone changes their display name.

Replay verification checks arithmetic and trading eligibility. It does **not** prove that someone avoided hindsight, owns a display name, or played through the interface. This is a historical learning game, not a contest with prizes. CORS is a browser policy, not authentication.

## Deploy when an account is available

Use a current Wrangler 4 release (4.36.0 or later for the rate-limit binding). From this directory:

```sh
cp wrangler.example.toml wrangler.toml
npx wrangler login
npx wrangler d1 create hetzerk-innovation-leaderboard
```

Put the returned database ID into `wrangler.toml`. Set `DATASET_URL` to the final commit-pinned URL for `data/innovation/dataset.json`. Set `DATASET_SHA256` to the SHA-256 of that exact file. From the repository root, the digest can be calculated with:

```sh
shasum -a 256 data/innovation/dataset.json
```

Do not use a moving branch or change the dataset without also changing its digest. A mismatch fails closed with a 503 response. Only configured server-side URLs are fetched; submissions cannot select a source. The current implementation serves one dataset version per Worker deployment. For concurrent historical boards, use separate versioned Worker deployments or extend the trusted version registry; never combine rankings across data versions.

Edit `ALLOWED_ORIGINS` to the exact site origins. It contains origins, not paths; `https://oftarradiddle.github.io` covers `/RED/innovation/`. Do not use `*`. For local review, add the specific local origin to a development config. Rate limiting is 20 requests per minute per method and source IP per Cloudflare location, using an account-unique namespace. The binding is required; missing database or limiter configuration disables the endpoint.

```sh
npx wrangler d1 execute hetzerk-innovation-leaderboard --local --file=schema.sql
npx wrangler dev
# After local review, provision the remote schema and deploy:
npx wrangler d1 execute hetzerk-innovation-leaderboard --remote --file=schema.sql
npx wrangler deploy
```

Set the repository Actions variable `INNOVATION_LEADERBOARD_URL` to the returned Worker base URL, with no trailing `/scores`, then run **Publish Hetzerk website** on `2026-sep-red`. All site publishing workflows pass that variable to the generated `innovation/config.json`. For a local build, set the same environment variable before `python -m publishing.build`. The page must disclose that a chosen display name, decisions and score will be published before submitting. Keep local-only mode if no endpoint has been configured. Do not put Cloudflare API tokens in page JavaScript, repository files or chat.

## Endpoint contract

`GET /scores?datasetId=innovation-v1-…` returns the top 20 entries for the configured dataset:

```json
{
  "datasetId": "innovation-v1-12345678",
  "asOf": "2026-09-25",
  "verification": "replayed-arithmetic",
  "scores": [
    {"name": "Example", "endValue": 123.4, "change": 0.234,
     "decisions": 65, "submittedAt": "2026-09-26T00:00:00.000Z",
     "replayId": "12345678", "benchmarkValue": 140,
     "startDate": "1960-01-04", "endDate": "2026-09-25"}
  ]
}
```

The example above illustrates a response shape; it is not a seeded score or an actual historical return. A fresh database returns an empty `scores` list.

`POST /scores` accepts `Content-Type: application/json` and exactly these fields:

```json
{
  "name": "Your alias",
  "datasetId": "innovation-v1-12345678",
  "actions": [{"opportunityId": "event-id", "amount": 25, "sells": []}]
}
```

Use `InnovationGame.score(data, state).replay.actions` for the actions and `InnovationGame.datasetId(data)` for the ID. The Worker forces starting capital and all rule settings. A new valid completed run returns 201; a duplicate returns 200 and the original entry. The response includes `score`, `duplicate`, `datasetId`, `asOf` and `verification`. Errors use `{ "error": "…" }` with 400 for invalid decisions, 409 for the wrong dataset, 413 for bodies over 64 KB, 422 for incomplete or stale-valued games, and 429 for rate limits. Public names allow 1–20 Unicode letters/numbers and basic punctuation. The UI must insert names with `textContent`, never raw HTML.

## Data handling and operations

Stored fields are the chosen public alias, canonical decisions, dataset version, computed balance/return, benchmark value, date horizon and submission time. The API does not expose full decision logs in its ranking response. It does not store IP addresses in D1, use cookies, collect emails or create accounts. Cloudflare may process request metadata under the operator's account settings. Data remains until the operator deletes it; publish the actual retention and contact policy before turning on public submissions.

The operator can remove an abusive alias or a requested entry with a parameterized administrative query through Cloudflare, keyed by dataset ID and the stored replay/run identifier. There is no unauthenticated deletion endpoint. Use D1 backups and account access controls. For a larger audience, add moderation and stronger abuse controls before inviting traffic; an anonymous alias is not a verified identity.

Tests use Node's built-in test runner with a small D1 mock:

```sh
node --test ../../tests/innovation-game.test.cjs worker.test.mjs
```

References: [D1 setup and bindings](https://developers.cloudflare.com/d1/get-started/), [prepared D1 queries](https://developers.cloudflare.com/d1/worker-api/d1-database/), and [Workers rate-limit bindings](https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/).
