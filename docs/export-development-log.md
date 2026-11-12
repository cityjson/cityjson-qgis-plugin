# Export Feature - Development Log

Process documentation of CityJSON export feature for the cityjson-qgis-plugin. Newest entries first.

How the feature works today: `docs/export.md`.

**Branch:** `cityjson-export` on `damandogra/cityjson-qgis-plugin`, based on `develop` plus
Gina's `cityjson-writter` dialog scaffold.

---

## Key decisions

| Decision | Why |
|---|---|
| **Patch the original instead of rebuilding from the layers** (proposal's Approach 2, without first building Approach 1) | QGIS layers are flat `MultiPolygonZ`. Rebuilding from them loses Solids, semantics, appearances, templates and unloaded LoDs. The import side already had subset code (`core/subset.py`) that copies objects and renumbers vertices, so patching was less work than writing a geometry writer. |
| **Geometry is read-only**; any geometry edit refuses the export | Measured (28 Oct): every vertex edit in QGIS broke the building, because a shared corner is a separate copy per face. Only a whole-object move was safe, and that has little use for 3D BAG data. |
| **Deleted vs never loaded** | Loading one LoD hides objects without it. No row means *deleted* only if the object had the loaded LoD; otherwise it was never loaded and is kept (optional drop). |
| **One object, many rows** | With LoD or surface splitting, an object survives if any LoD row survives. Deleting only some surface rows is refused (it would change topology). |
| **Stamp each layer with its source and load settings** | The exporter receives layers but needs the original file. Layer names can be renamed; custom properties can't be lost that way. |
| **One session only** | Measured: stamps survive a project reopen, memory-layer rows don't. Export refuses empty layers. |
| **Processing algorithm first, menu dialog second** | The algorithm is testable headlessly; the dialog is then a thin wrapper. |
| **Area filter uses the load-side rule** | Keep whole objects by centroid, never clip polygons, so geometry can't break. |

---

## 2026-11-12 : Dialog tests

- Review feedback: no tests for the interface. The menu dialog had been treated as a thin
  wrapper checked by hand, but `export_cityjson()` grew its own checks.
- `tests/test_cityjson_writer_dialog.py`: widgets, defaults, save mode, `reset_fields()`,
  dialog hides while drawing an area, Close button.
- `tests/test_cityjson_loader.py` `TestExportDialog`: `write()` lists one entry per loaded
  file; Convert warns on missing input, refuses overwriting the source and inherited parent
  attributes, shows exporter errors, passes options and the area (converted to the layer's
  CRS), reloads only when asked and something was exported.
- Not fixed: `reset_fields()` doesn't untick "Add saved file to map".
- 344 passed (local QGIS 3.44).

## 2026-11-01 : Minor edits

- PR target is `develop`: upstream has no `development` branch. Fixed the typo in
  `CONTRIBUTING.md`. CI runs on PRs to `develop`, so the PR will be tested.
- Output written compactly (`separators=(",", ":")`); it was 10–15% larger than the source.
- Parent resurrection now walks every level (Building → BuildingPart → Installation).
- `process_templates` / `process_appearance` crashed on objects without `geometry` (e.g.
  `CityObjectGroup`); now `.get("geometry", [])`.
- "Add saved file to map" skips an empty export (the loader crashes on an empty model).
- 323 passed.

## 2026-11-01 : Layer provenance and menu export

- **Stamps:** `CityJSONLoader` passes a `provenance` dict to `DynamicLayerManager`, which sets
  `cityjson/source`, `load_id`, `lod`, `semantic_surfaces`, `keep_parent_attributes` on every
  layer (strings, `json.dumps`).
- **Measured:** stamps survive a project save/reopen, memory-layer rows don't (722 → 0, tile
  `10-282-560`; QGIS warns about scratch layers).
- `read_provenance(layers)`: groups by `load_id`, reads stamps, refuses a group with 0 rows.
  Not in `export()`, where an all-deleted export legitimately returns `{}`.
- The plugin's model cache is not used: it isn't filled by the Processing load path, so export
  re-reads the stamped source file.
- **Menu dialog:** one entry per loaded file, exports all its layers together. Keep/drop
  unloaded checkbox (default keep), "Add saved file to map", area filter (`QgsExtentWidget`,
  box in the layer's CRS). Refuses overwriting the source and `keep_parent_attributes`
  (`ParentFeatureDecorator` copies parent attributes into children; export would save them).
- **Area filter:** `CityJSONExporter(bbox=...)` keeps objects whose centroid is inside, plus
  their parents/children; `prune_dangling_children` cleans the rest.
- **Tile `10-282-560`, LoD 2.2, one building deleted:** keep 7.1 MB, drop 4.8 MB, area 480 KB.
  All cjval valid (warnings: duplicate vertices from the source).
- 321 passed.

## 2026-11-01 : Processing algorithm

- `processing/cityjson_export_algorithm.py`, registered in `provider.py`. Toolbox: CityJSON
  Loader → Export → Export CityJSON. User enters the load settings by hand.
- Exporter errors become `QgsProcessingException`; nothing written on failure. Refuses
  output == source (after overwriting a source tile once).
- `test_provider_algorithm_properties` used `algorithms[0]`; QGIS doesn't keep order → look up
  by name.
- **Tile `10-282-560`, one building deleted:** first run left its LoD0-only parent `Building`
  as a childless footprint (never loaded → kept). Fix `cb22d9a`: drop a never-loaded parent
  when all its children were deleted (one level). 1443 → 1441 objects; all others identical.
- cjval: valid; duplicate vertices 1424 → 1422 (from the source), no unused vertices.

## 2026-11-01 : Geometry edits refused

- Each row's geometry is rebuilt from the original and compared corner by corner within
  `scale / 2` (0.5 mm for 3D BAG): absorbs float noise, catches any real edit.
- Any difference → `ValueError` naming every edited object, before writing.
- Covers all load modes: no LoD field, LoD rows, surface rows. Doesn't rely on the edit buffer
  (empty once edits are saved to the layer).

## 2026-10-28 : What QGIS editing does to geometry

Question: can users edit geometry in QGIS and export it? Measured instead of assumed.

**Checker:** `scripts/check_geometry.py` flags non-planar, degenerate and self-intersecting
faces. Planarity = max corner distance to the Newell plane; tolerance 1 cm (val3dity's
`planarity_d2p_tol` default). 30 tests, no QGIS needed. Limit: per face only, blind to cracks.

**Baseline:** tile `10-284-560` (23,156 faces) is clean at 1 cm (worst 3.5 mm); 18 degenerate
+ 1 self-intersecting face, all in buildings val3dity also flags. Loaded in QGIS: same results,
same face order as the file.

**Experiment** on `NL.IMBAG.Pand.0503100000022502-0` (15 faces, 70 corners), QGIS 3.44.13:

| Edit | Corners | Worst dev. | What broke |
|---|---|---|---|
| Move whole building | 70 → 70 | 0.33 mm | nothing |
| Lift corner +0.5 m (wall copy) | 70 → 70 | 0.33 mm | crack; checker blind |
| Lift corner +0.5 m (roof copy) | 70 → 70 | 22.6 cm | roof bent + crack |
| Drag corner ≈1 m | 70 → 70 | 3.1 cm | face bent + crack |
| Delete vertex | 70 → 69 | 0.33 mm | quad → triangle, gap |
| Reshape | 70 → 76 | 6.4 m | new corners at z = 0; floor and roof both hit |
| Add vertex on edge | 70 → 71 | 0.33 mm | neighbouring face lacks the corner |

**Findings**
- Only moving a whole building is safe.
- A corner shared by n faces is n separate copies in the flat `MultiPolygonZ`; every vertex edit
  moves one copy → crack. Structural, not precision.
- In 2D you can't choose which stacked height you edit; Reshape invents z = 0.

**Decision:** geometry is read-only. Dropped: vertex-move editing (planned before this
measurement) and whole-object moves (low value for 3D BAG, 1–2 days of work).

## 2026-10-25 : One object, many rows

- One object can be several rows (per LoD, per semantic surface). `_count_rows()` →
  `{(uid, lod): n}`.
- **LoD rows:** object survives if any row survives; geometry entries whose row was deleted are
  dropped. LoD compared as `str()` (CityJSON 1.0 stores numbers).
- **Surface rows:** caller passes `semantic_surfaces=True` (layers don't show it). All rows gone
  → dropped; some gone → `ValueError`.
- Faces counted with `read_boundaries(..., None, None)`, not `get_polygons` (which returns 0
  with an empty `VerticesCache`).
- Objects without a `geometry` key no longer get `"geometry": []`.

## 2026-10-24 : Fidelity test

- Fixture: LoD2 Solid with semantics + material, plus unloaded LoD1, appearance, metadata.
- Delete one building, export: Solid, semantics and LoD1 kept; materials reduced and renumbered;
  metadata unchanged. No exporter changes needed, which confirms the patch approach. cjval valid.

## 2026-10-23 : Unloaded LoDs

- **Problem:** loading one LoD skips objects without it; export read "no row" as deleted, so a
  LoD2-only tree vanished when LoD1 was loaded.
- **Fix:** `loaded_lod` + `keep_unloaded`. Using the loader's `has_lod()`: loaded + no row →
  deleted; never loaded → kept (or dropped if `keep_unloaded=False`, along with unloaded
  geometry entries).
- **Gotcha:** `has_lod` matches exactly `"All"`; `"ALL"` resurrected every deleted object.

## 2026-10-19 : cjval

- Two-cube round trip: valid, no warnings, no unused vertices.
- Exporter doesn't deduplicate vertices; it inherits the source's duplicates.
- cjval checks structure, not geometry (that's val3dity).

## 2026-10-19 : Copy bug and attribute edits

- **Copy bug:** `get_subset_cotype` copies by reference and `process_geometry` rewrites indices
  in place, so export corrupted the model still loaded in QGIS. Fix: deepcopy each surviving
  object. Test: export twice, outputs equal, original unchanged.
- **Attributes:** written only when they differ from the stringified original, so untouched
  values keep their type (int stays int, missing stays missing). Edited lists/dicts go through
  `json.loads`; invalid JSON → `ValueError`.
- Fixed two broken tests (one nested inside another, one `=` instead of `==`).

## 2026-09-20 : Round trip green; branch repairs

- **Approach changed:** instead of a geometry writer, `export()` reuses the import-side subset
  code: copy surviving objects (found by `uid` in the layers), then `process_geometry`,
  `process_templates`, `process_appearance`, metadata. Mirrors `get_subset_cotype`.
- `prune_dangling_children` removes children that were deleted.
- **Branch repairs:** the `cityjson-writter` merge brought back a dead `from .resources import *`
  (31 tests errored) and Qt-resource icon paths (both icons blank). Fixed: import commented
  out, icons loaded from disk. `test_initGui` updated for the second menu action. Unnoticed
  because CI only runs on `develop`.
- `core.autocrlf = input` (Windows line endings showed as 264-line diffs).

## 2026-09-09 : Round-trip test first

- Merged `cityjson-writter` + `develop` (v1.0.1) into `cityjson-export`.
- Round-trip test (load → delete one building → export → reload) written red first; it fixed
  the API: `CityJSONExporter(layers, citymodel=...).export()` and
  `save_cityjson_model(dict, path)`.

## 2026-08-13 : Setup

- Branch `cityjson-export` off `cityjson-writter` (Gina merged `develop` into it on 7 Aug,
  `98d21c2`). Gina confirmed she is done with that branch.
- Repo symlinked into the QGIS plugin folder; edits run live.
- One branch for the whole feature. `Changelog.md` untouched until PR.
- `resources.py` is generated but not in `.gitignore`. Left for now.

---

## How to test

```powershell
docker build -f docker/Dockerfile.qgis-3.40 -t cityjson-qgis-plugin-test-340 .   # once
docker run --rm -v "${PWD}:/app" cityjson-qgis-plugin-test-340
```

Validate exports at https://validator.cityjson.org (cjval).