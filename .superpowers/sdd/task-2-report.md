# Task 2 Report: 新增 /ortho-portal 路由 + HTML 骨架

## What was implemented
- Added `GET /ortho-portal` route in `web_server.py` (after `/ortho`, before `/pharmacy`)
- Created minimal `ui_ortho_portal.html` skeleton (served by the route)
- Added `TestPortalRoute` class (2 tests) to `tests/integration/test_ortho_portal.py`
- Set `HAIP_TEST_MODE=true` in test file to bypass AuthMiddleware

## TDD RED/GREEN evidence

### RED (Step 2)
```
$ python -m pytest tests/integration/test_ortho_portal.py::TestPortalRoute -q
FAILED tests/.../test_ortho_portal.py::TestPortalRoute::test_route_returns_200
FAILED tests/.../test_ortho_portal.py::TestPortalRoute::test_route_is_html
2 failed — 404 (route not defined)
```

Note: initial run gave 401 (auth middleware), not 404. Fixed by adding `os.environ["HAIP_TEST_MODE"] = "true"` before app import. After that, got expected 404.

### GREEN (Step 5)
```
$ python -m pytest tests/integration/test_ortho_portal.py -q
8 passed (6 Task-1 + 2 new PortalRoute) in 0.89s
```

## Files changed
| File | Action |
|------|--------|
| `packages/haip-core/haip/web_server.py` | Inserted `/ortho-portal` route (lines 587-592) |
| `packages/haip-core/haip/ui_ortho_portal.html` | Created — minimal HTML skeleton |
| `tests/integration/test_ortho_portal.py` | Added `TestPortalRoute` class + `HAIP_TEST_MODE` env var |

## Self-review
- Route pattern matches existing `/ortho` route conventions exactly
- `HTMLResponse` and `Path` already imported (lines 10, 21)
- Test file preserved all existing Task-1 tests (6 passing)
- Only 3 files staged and committed explicitly

## Concerns
- None. Task complete per brief.
