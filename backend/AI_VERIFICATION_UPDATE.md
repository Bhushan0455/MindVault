# Live AI verification update

Role B estimate: approximately **98%**. Evidence source: the user's pasted terminal output for the built-in fictional four-stage diagnostic, using `gemini-3.6-flash`.

## Earlier diagnostic, before the schema adjustment

| Service | User-observed result |
|---|---|
| Plain-text connection | Verified |
| Knowledge extraction | Not verified; INVALID_ARGUMENT, then deterministic_fallback with five locally extracted pending candidates |
| Content review | Verified for this fixture; ai_used=true, completed, one retained AI finding |
| Clarity audit | Verified for this fixture; ai_used=true, completed, one retained AI proposal |

These are standalone diagnostic results. The diagnostic did not save credentials or enable AI in the running API. They do not establish general model accuracy or verify the website.

## Current acceptance result

The user's extraction retry succeeded with `method=ai`, five validated pending candidates and zero validation issues. All three standalone services are now verified for their fictional fixtures.

The agent then exercised the actual running API using a separate clearly fictional brand. The client did not read the Gemini key; the API used its existing private configuration. Metadata-only evidence is in `verification/live-api-ai.json`:

- Knowledge extraction: `method=ai`, seven pending candidates.
- Content review: `ai_used=true`, one retained AI finding with exact original-text spans and a source from the uploaded fixture; the deterministic ₹799 → ₹999 price finding was retained.
- Clarity: `ai_used=true`, two source-validated pending AI proposals.

Only manually specified fictional fixture knowledge was approved to set up the test. AI-extracted candidates and rewrites remain pending. No content was approved, submitted or published by this AI verifier.

The former health value `live_ai_verified=false` was hardcoded. It has been removed and replaced with `ai_verification_scope=per_service_result`. Restart the server once to load that response correction. Health confirms configuration; inspect each review/job response for actual AI activity.

## Extraction compatibility adjustment

The extraction request uniquely placed `maxItems: 100` around a candidate structure containing 16 required payload strings. The provider-facing schema now omits that array bound, while the canonical schema and `validate_candidates` continue enforcing at most 100 candidates. Exact source quotes, allowed fields, values, units, scope and pending-only validation are unchanged. Over-limit provider output is rejected and uses the labelled deterministic fallback.

This targets a possible schema-complexity issue. Google [documents that complex structured-output schemas may be rejected](https://ai.google.dev/gemini-api/docs/structured-output?lang=rest). The generic INVALID_ARGUMENT response does not prove that this particular constraint caused the rejection; the subsequent successful live CLI and API retries now confirm that the adjusted request works for these fixtures. They do not independently isolate every cause of the original generic error.

Tests verify the outgoing request shape, unchanged canonical validation and SDK configuration. The full suite passes on PostgreSQL and SQLite, including the user's Python 3.14 environment. The agent's separate live API acceptance check used the server's configured provider without reading its key; the automated regression tests use provider boundary fakes.

## Reproduce the extraction diagnostic

In the existing integrated backend folder, run:

```powershell
.\.venv\Scripts\python.exe -m examples.gemini_setup --connect --model gemini-3.6-flash --timeout-seconds 45
```

Enter the key through the hidden prompt. This default mode tests knowledge extraction only; it avoids repeating the already successful content/clarity requests. Look for `method=ai` and `LIVE GEMINI VERIFIED` with source-validated pending candidates. `deterministic_fallback` does not verify extraction. If it fails, retain the redacted diagnostic output for the next investigation.

## Reproduce the API acceptance check

With the configured local demo API running, execute:

```powershell
.\.venv\Scripts\python.exe -m scripts.ai_api_smoke http://127.0.0.1:8000 --report verification/live-api-ai.json
```

This makes live model requests, creates a new fictional brand and its fixture records, and saves metadata-only results. It never reads the provider key and has no mock fallback. Empty valid model output may be inconclusive for a fixture; deterministic fallback does not count as AI verification. Re-running is optional because this check has already passed. Actual frontend/browser and staging acceptance follow.
