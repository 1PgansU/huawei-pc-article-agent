# QA Integration Report

## Summary
- Total Tests: 17 | Passed: 12 | Failed: 5
- Coverage: Critical API, static frontend, basic generation/revision/export paths, round-2 regression, late targeted fix check (integration smoke coverage)
- Routing Decision: Known Issues (round 2 complete; channel-length bug remains)

## Passed
- Python compilation: `api_server.py`, `agent/service.py`, and domain layer modules.
- JavaScript syntax: `frontend/js/api-client.js` and `frontend/js/app.js`.
- Server starts with `D:/anaconda3/python.exe`; `GET /api/status` returns live status, masked client ID, probes, and explicit template/local mode.
- `GET /api/options`, `/`, and `/js/api-client.js` return HTTP 200; options include products, eight scenarios, and four platforms.
- `/api/task/validate` accepts complete input; `/api/plan` preserves audience, goal, stage and maps Chinese enums. Missing fields and unknown product are rejected (HTTP 422).
- `POST /api/generate` returns a complete result bundle with `local_index`/`template`, evidence and real-image asset URLs; report is WARN for local mirror.
- High-risk CTA revision (`保证最低价999元`) is marked FAIL; `POST /api/export` blocks it with HTTP 409 `EXPORT_BLOCKED`.
- Registered image asset serves HTTP 200; unknown asset returns 404. Stale revision returns HTTP 409.

## Failed Tests
- Valid channel revision fails generation contract: starting from a generated 小红书 draft, revise with `{"platform":"公众号"}` returns version 2 but `report.overall=FAIL`, with `fact_check` issue `字数过短（398 < 1500）`. The body is 398 characters against the 公众号 minimum. Source: `agent/layers/article_generation.py` generation strategy / length handling (verify exact implementation location). Engineer notified; this prevents a valid channel change from producing an exportable draft.
- The response-envelope issue was fixed after round 2: targeted verification now receives `{data, request_id}`.

## Known Issues
- Round 2 reproduced the channel revision failure at 398 characters. A late padding fix improved it, but targeted regression still returns `report.overall=FAIL`: verifier length 1366 versus the 公众号 minimum 1500. Image and compliance checks pass, but export remains blocked.
- The documented success response envelope is now fixed and verified.

## Notes
- Request validation errors use structured `error` and `request_id`; unknown product is HTTP 422. `POST /api/task/validate` represents invalid field input in a 200 response with `valid:false`, consistent with its validation-style endpoint.
- External ima connection was available in this environment, but retrieval used `local_index`; online media/source validation is not established by this run.
- The strict two-round limit is reached. No business source files were modified by QA.
