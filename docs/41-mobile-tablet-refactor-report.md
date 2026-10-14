# Mobile and tablet refactor - final report

Branch: `feature/mobile-tablet-refactor`

Commits:
- `d1bff076` UX fixes: hub tiles, sidebar, plan header, filters, breadcrumb, Issue Board
- `92181ef4` Fit popups to the viewport on small screens
- the report commit that adds this file

## Changed

Shared helpers (`tools/build_helpers.py`, `tools/doc_upload.py`, `tools/domain_parts.py`):
- `capped_body(name, kids, max_h)`: popup body that scrolls vertically and is capped by the viewport.
- `popup_body_max(fixed_h, ...)`: `App.Height` minus the fixed chrome (header, footer, margins).
- `build_paste` (Equipment, Material, Measuring Point) and `Functional Location App/build/fl_parts.py`: paste popups use `capped_body`; gallery and help heights depend on `if_below("Tablet")` / `at_least("Desktop")`.
- `Maintenance Plan App/build/build_tasklist.py`: Materials popup body capped.
- `Maintenance Plan App/build/build_items.py`: object-list gallery height capped by `App.Height`.
- `Maintenance Plan App/build/build_modal.py`: long-text box height capped by `App.Height`.

Regenerated: ScreenEquipment, ScreenFunctionalLocation, ScreenMaterial, ScreenMeasuringPoint, ScreenVhPlan.

## Patterns

- Viewport tiers from `layout_tokens.BREAKPOINTS` (Mobile 0, Tablet 720, Desktop 1024, Wide 1600) via `below()`, `at_least()`, `if_below()`.
- Popups: fixed header and footer, the body is the only scrolling region and is limited by `App.Height`.

## Expand/collapse

Existing expand/collapse sections were preserved; none removed. Marker counts per screen: Equipment 5, Functional Location 5, Issue Board 6, KKS 5, Material 5, Masterdata Hub 6, Maintenance Plan 5, VH Plan 9.
Masterdata Hub switchers were not changed.

## Validation

- `python tools/build_all.py`: OK
- `tools/check_layout.py` on all 8 BIO SAP screens: OK (pre-existing advisory [15] ForAll Patch/Collect remain)
- `PYTHONUTF8=1 python -m pytest tests -q`: 531 passed, 23 skipped
- New `tests/test_popup_viewport_cap.py` asserts that the popup bodies are capped by `App.Height`.

## Not verified / limitations

- No visual or interaction testing in Studio at mobile/tablet viewports. Layout was checked statically (`check_layout` at several widths, yaml analysis, tests). Individual buttons, tabs and popup actions were NOT clicked through on devices.
- Feedback popup head scrolls with its content (reachable, but not sticky).
- Materials popup table keeps its own horizontal scroll (pre-existing, wide table).
- The audit of touch targets, gallery scrollbars, nested scrolling and keyboard overlap was not exhaustive.
- The computer was NOT shut down because the shutdown conditions (full interaction tests, post-deploy smoke test) cannot be met from this environment.

## Deployment

See the section below (updated after the deploy attempt).

### Result

`python tools\canvas_mcp.py deploy --app biosap --clean` completed: "Faerdig. Traeet i Studio er det byggede."; all 8 screens report "samme trae" (Studio tree identical to the built tree). No post-deploy click-through smoke test was performed (see limitations).
