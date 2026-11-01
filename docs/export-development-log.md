# Export Feature — Development Log

Decisions and dead ends, newest first. Not a release changelog (`Changelog.md` is that, and
gets one entry at PR time). Keep entries short — what changed, why, what's blocked.

---

## 2026-11-01 — X15 menu export

- `read_provenance(layers)`: groups layers by `load_id`, reads stamps back, refuses a group
  with 0 rows (reopened project). Not in `export()`: a legit all-deleted export returns `{}`.
- Menu dialog wired: one dropdown entry per loaded file, exports all layers of that
  `load_id` together; no source/LoD/semantics inputs. Refuses overwriting the source and
  `keep_parent_attributes` (exporter would copy parent attributes into children).
- Real tile `10-282-560`, one building deleted: cjval valid, warnings only (duplicate
  vertices, from the source; same as X14). 318 passed.
- Not wired yet: "Add saved file to map" checkbox; keep/drop unloaded LoDs (fixed to keep).
- For Gina: refuse inherit-parent-attributes, or skip inherited values on export?

## 2026-11-01 — X15 stamping

- Layers stamped at load with `cityjson/source`, `load_id`, `lod`, `semantic_surfaces`,
  `keep_parent_attributes` (`DynamicLayerManager`). 316 passed.
- Measured: stamp survives project save/reopen, memory-layer rows don't (722 → 0,
  tile `10-282-560`). Export works within one session only.
- Open: refuse export when a `load_id` group has 0 rows (reopened project).
- Next: helper that groups layers by `load_id`, reads stamps, applies the 0-rows check.


## X14 — export as a Processing algorithm (1 Nov)
- new `processing/cityjson_export_algorithm.py`, registered in `provider.py`; toolbox: CityJSON Loader → Export → Export CityJSON
- inputs: layers, original file, loaded LoD(s), keep unloaded, semantic surfaces, output file — user must repeat the load settings (provenance is X15)
- exporter `ValueError`s re-raised as `QgsProcessingException`; nothing written on failure
- refuses output path == source path (I overwrote the source tile once)
- `test_provider_algorithm_properties` took `algorithms[0]`; QGIS doesn't keep insertion order → look up by name
- tests: metadata, parameters, invalid file, kwargs to exporter, export error, overwrite guard, end-to-end headless run (real context/feedback, no mocks)

**Real tile** — `10-282-560` (3D BAG v2025.09.03), LoD 2.2, no semantic surfaces, deleted one building
- first run 1443 → 1442: only `NL.IMBAG.Pand.0503100000025720-0` (BuildingPart) removed; its parent `Building` (LoD0 only) kept, childless
- cause: parent has no LoD 2.2 → "never loaded" → kept by `keep_unloaded`
- fix (`cb22d9a`): a never-loaded parent is dropped when it has children and all were deleted by the user; kept if any child survives or was never loaded. One level only (enough for 3D BAG)
- after fix 1443 → 1441, parent gone
- other 1441 objects: attributes and resolved geometry identical; transform, metadata identical; no dangling parents/children

**cjval v0.10.0** — original and export both "valid, with warnings", no errors
- duplicate vertices 1424 → 1422 (already in the source; 2 left with the deleted part)
- unused vertices 0 → 0 (compaction OK, 64153 → 64014)

**Open for Gina**
- parent-drop rule (`cb22d9a`): right behaviour, or keep the footprint?
- old `Export CityJSON...` menu dialog is still the `cityjson-writter` stub — looks like export, does nothing (X15)
- minor: `save_cityjson_model` writes with spaces → 6.8 MB vs 6.1 MB; `separators=(",", ":")` would fix it


## X10 — geometry edits detected and refused (1 Nov)
- export rebuilds each row's geometry from the original model (same reader path as import) and compares corner by corner within scale/2
- any difference → ValueError naming every edited uid, before anything is written
- covers all three load modes: no lod column, LoD rows, surface rows
- tests: untouched, moved building, lifted vertex, deleted vertex, sub-half-step move, LoD rows, surface rows
- open for Gina: objects with a single face never appear as surface rows (layers.py:547)


## 2026-10-28 — X9: what QGIS editing does to CityJSON geometry

**Setup**
- Tile `10-284-560` (3D BAG v2025.09.03), loaded with the plugin: LoD 2.2,
  no LoD field, no semantic surfaces, one layer. 12,204 faces.
- Checked the unedited layer with `faces_from_layer`: identical to the file
  (same 18 degenerate + 1 self-intersecting faces, **same face numbers**).
  Confirms the plugin keeps faces in file order, which X12 depends on.
- Test building: `NL.IMBAG.Pand.0503100000022502-0`, 15 faces, 70 corners,
  worst deviation 0.33 mm, val3dity clean.
- Each edit: snapshot → edit → snapshot → discard. Measured faces, corners,
  worst deviation, broken faces, corners changed, split corners (copies of
  one original corner that no longer agree).

**Results**

| # | Edit | How | Corners | Changed / split | Worst dev. | What broke | Tier |
|---|---|---|---|---|---|---|---|
| 1 | Move building 2D (Move Feature) | mouse | 70 → 70 | all / 0 | 0.33 mm | nothing | 1, clean |
| 2 | Lift corner +0.5 m, wall copy | typed (Vertex Editor) | 70 → 70 | 1 / 1 | 0.33 mm | crack between faces; checker blind | 1, broken |
| 2a | Lift corner +0.5 m, roof copy | typed (Vertex Editor) | 70 → 70 | 1 / 1 | 22.6 cm | roof non-planar + crack | 1, broken |
| 2b | Drag corner ≈1 m sideways | mouse (Vertex Tool) | 70 → 70 | 1 / 1 | 3.1 cm | sloped face non-planar + crack | 1, broken |
| 3 | Delete a vertex | mouse + Delete | 70 → 69 | – | 0.33 mm | face 14 quad → triangle; gap to neighbours; checker blind | 2 |
| 4 | Reshape across an edge | mouse, 2D line | 70 → 76 | – | 6.4 m | new corners at z = 0; floor and roof both reshaped, walls not | 2 |
| 5 | Add vertex on an edge | mouse, double-click | 70 → 71 | – | 0.33 mm | z interpolated correctly (0.7); wall above doesn't get the corner | 2 |

**Findings**
1. **Only moving a whole building is safe.** Every other edit broke the building.
2. **A shared corner is several independent copies.** The plugin loads each face
   as its own polygon in a flat `MultiPolygonZ`; a corner shared by 3 faces is
   3 copies. Every vertex edit moved exactly 1 copy → a crack. Typed and mouse
   edits behave the same, so this is structural, not a precision problem.
3. **In 2D you can't choose the height you edit.** Copies at z 0.70, 7.20 and
   9.11 sit on the same x, y spot; the Vertex Tool picked face 14 every time.
4. **2D drawing tools invent heights.** Reshape puts new corners at the default
   z (0) and interpolates toward it at the edge crossings (0.35, 4.55). Adding
   a single vertex on an edge interpolates correctly.
5. **Reshape and vertex tools hit every face under the cursor in 2D.** Floor
   and roof overlap from above, so both changed while the walls did not.
6. **Vertical walls hide z edits.** Lifting a wall corner keeps the wall
   planar (its plane contains the up direction), so the checker sees nothing.
7. **The per-face checker catches bent faces only.** Cracks, gaps and
   mismatched topology are shell-level (val3dity 302-type) and invisible to it.

**Consequence for X10–X13**
- "Tier 1 = face and corner counts unchanged" is not enough: edits 2, 2a and
  2b keep the counts and still break the building.
- X10 needs a third outcome besides Tier 1 / Tier 2: **split vertex**
  (copies of one original vertex index now disagree). X12's lockstep walk
  already maps every QGIS corner back to its index, so this is cheap to detect.
- Options: (A) refuse split vertices with a clear error; (B) propagate:
  if all moved copies agree, move `vertices[index]` once, then run the
  checker on that object and warn. Proposal: A first, B later.
- Export must also round edited coordinates to the file's 1 mm grid (X11);
  edit 1 produced `84801.98421033…`.

**questions for Gina**
- Refuse or propagate split vertices (A vs B)?
- Is vertex-move editing still worth shipping, given that only a whole-object
  move is safe in practice? Alternative: support whole-object moves only.

**Decision (28 Oct)**
- Geometry is read-only: export detects any geometry edit made in QGIS and
  refuses with a clear error (X10). Old X11–X13 (vertex-move editing) dropped.
- Considered and dropped: refusing vs propagating split vertices (A/B), and
  supporting whole-object moves (low value: 3D BAG footprints come from the
  BAG register; would cost 1–2 days).
- To confirm with Gina.

**Limits of this experiment**
- One building, one tile, QGIS 3.44.13, LoD 2.2 only.
- Edit 2a's 22.6 cm was predicted by simulation and then measured identically.
- No screenshots of the 3D view yet.




## 2026-10-28 — X9: geometry checker and 3D BAG baseline

- `scripts/check_geometry.py`: flags non-planar, degenerate and self-intersecting
  faces in a CityJSON file. 30 tests in `tests/test_check_geometry.py`, no QGIS needed.
- Planarity: Newell normal + centroid, max corner distance to the plane.
  Default tolerance 1 cm = val3dity `planarity_d2p_tol` default; report also
  counts at 1 mm and 5 cm. Known limit: one corner lifted by h shows as ≈ h/4.
- Baseline, unedited 3D BAG tile `10-284-560` (23,156 faces):
  - non-planar: 0 > 1 cm, 16 > 1 mm, worst 0.35 cm
  - degenerate (repeated corner): 18 faces in 5 buildings
  - self-intersecting (touching edges): 1 face in 1 building
- Cross-checked against the tile's own `b3_val3dity_lod22`: every flagged face
  is in a building val3dity also flags (102 / 104), no false alarms.
  Missed: 2 buildings with 102 (val3dity likely snaps corners within 1 mm; the
  checker uses exact equality), and shell-level 302/303 (out of scope, the
  checker works per face).
- **Clean at 1 cm**, so any non-planar face after a QGIS edit is caused by the edit.
- Next: the experiment. Load this tile in QGIS, do the 4 edits, check each.


## 2026-10-25 — X6: one object, many rows

- **Problem:** one CityObject can become several QGIS rows (per LoD via
  `LodFeatureDecorator`, per face via `SemanticSurfaceFeatureDecorator`). Export only
  collected uids, so it couldn't tell which LoD or how many faces were deleted.
- `_count_rows()`: `{(uid, lod): n}`, `lod = None` when the layer has no `lod` field.
  `get_surviving_ids()` now reads its uids from it.
- **Rule 1 (LoD rows):** the object survives if any row survives; geometry entries whose
  LoD was loaded but lost its row are dropped, before `process_geometry`. Skipped when
  `lod_as="NONE"` (no `lod` field). LoD compared as `str()`, since the field is text and
  CityJSON 1.0 stores numbers.
- **Rule 2 (surface rows):** new `semantic_surfaces=False` flag; the layers don't show
  whether surfaces were split into rows (no `surface.*` fields if the model has no
  surface attributes), so the caller must say so. `_check_surface_rows()` compares rows
  to faces in the original: all gone → dropped, none missing → kept, some missing →
  `ValueError` naming the object. Runs before any copying.
- Faces counted with `read_boundaries(boundaries, None, None)` (index-only), not
  `get_polygons`: with the exporter's empty `VerticesCache`, `get_polygons` swallows the
  `IndexError` and returns 0. `GeometryInstance` counted via its template. Expected is
  at least 1, matching the loader's `len(polygons) > 1` split.
- Objects without a `geometry` key no longer get `"geometry": []` added (fixed in the
  X7b drop loop too).
- **Known behaviour:** a parent whose row was deleted but whose child survives is kept,
  with its loaded geometry dropped.
- **Still open:** pass `semantic_surfaces` from the UI or Processing algorithm (X14, X15).
- **Tests:** (a) delete house_a's LoD1 row → only LoD2 kept, house_b untouched;
  (b) delete one surface row of building1 → raises; (c) delete all of building2's
  surface rows → building2 dropped, building1 kept. Helpers `_delete_lod_row`,
  `_delete_all_rows`.
- 268 passed.


## 2026-10-24 — X7: fidelity test

- `_cube_solid(first_vertex)` + `_fidelity_citymodel()`: building1 = LoD2 Solid with
  semantics + material 1, plus LoD1 MultiSurface; building2 = same shape, material 0.
  Two materials, metadata.
- Test: load `lod="2"`, delete building2, export with `loaded_lod="2"`. Passed with no
  exporter changes: Solid kept (1 shell, 6 faces), semantics unchanged, materials reduced
  to the used one and renumbered 1 → 0, unloaded LoD1 kept, metadata unchanged.
- Covers the appearance / metadata branches of `export()` flagged as unexercised on 19 Oct.
- cjval: 100% valid.
- Geometry not checked with val3dity: export copies it verbatim, so it would only test the
  fixture. Use val3dity from X9 onward, when export changes coordinates.
- Regression net for X10–X13.
- 265 passed.


## 2026-10-23 — X7b: unloaded LoDs on export

- **Problem:** loading at one LoD (e.g. `lod="1"`) skips objects with no geometry at that
  LoD (`core/loading.py:182`), so they never get a QGIS row. Export treated "no row" as
  "deleted", so a LoD2-only object (e.g. a tree) was silently dropped, while unloaded
  LoDs of loaded objects were kept. Inconsistent, and the user never deleted it.
- **Fix (export-side only):** `CityJSONExporter` takes `loaded_lod` (default `"All"`) and
  `keep_unloaded` (default `True`). It re-checks each object with the loader's own
  `GeometryReader.has_lod()`:
  - has loaded LoD + no row → deleted by user → dropped
  - no loaded LoD → never loaded → kept if `keep_unloaded`, else dropped
- **Drop mode** also removes unloaded geometry entries from surviving objects, before
  `process_geometry`, so their vertices are compacted out.
- Commits: `719eb4c` (keep), `2849ddb` (drop).
- **Tests:** fixture `_unloaded_lod_citymodel()` (house_a, house_b: LoD1+LoD2; tree:
  LoD2 only). Keep test: tree kept, house_b gone, house_a has 2 LoDs. Drop test: tree
  gone, house_a only LoD1. Load via `loader.load()`, not manual `add_object`, or the
  skip at line 182 is bypassed.
- **Gotcha:** `has_lod` matches exactly `"All"`; a default of `"ALL"` resurrected every
  deleted object (3 tests failed).
- 264 passed.
- **Next:** `loaded_lod` / `keep_unloaded` need to be exposed in the UI (X14 parameter,
  X15 dialog); run cjval on both outputs.



## 2026-10-19 — X8: cjval validation

- Validated round-trip output (two cubes, building2 deleted) at validator.cityjson.org (cjval WASM, schemas v2.0.2).
- Output: 100% valid — no errors, no warnings. `unused vertices` clean → `process_geometry` compaction works.
- Input fixture: valid, 4 `duplicate vertices` warnings — the cubes share a face at x=1000 and `_cube_vertices` writes each cube's corners separately. Fixture quirk, not exporter.
- Exporter doesn't dedup; it inherits whatever the original had.
- Limits: cjval checks schema/structure only, not geometry (planarity, solids → val3dity). Fixture has no Solids/semantics/appearance, so those checks weren't exercised.
- Next: re-run on X7's fixture once it exists.


## 2026-10-19 — X4 and X5 done, tests repaired

- X4: export() deepcopies each surviving CityObject (`5e79164`, 23 Sept).
  get_subset_cotype assigns by reference and process_geometry rewrites
  indices in place, so without it export corrupts the live model.
- X4 test: delete building1, export twice, assert both outputs equal and
  the original unchanged. Verified red with the deepcopy removed.
  Needed the delete — with both cubes surviving, indices 0-15 compact onto
  0-15 and the bug is invisible.
- X5: apply_attribute_edits only writes a field if it differs from the
  stringified original, so untouched values keep their type (int stays int,
  missing stays missing). Edited dicts/lists go through json.loads; invalid
  JSON raises ValueError naming the object and field.
- Fixed in exporting.py: uid lookup ran before its `in` guard.
- Fixed in test_export.py: one test was nested inside another and never
  ran; attribute test used `f["uid"] = ...` (assignment) instead of `==`.
- 262 passed.

Still open:
- transform and metadata are copied by reference (harmless today).
- Coverage: appearance / metadata / geometry-templates branches in export()
  are never exercised. That's X7.
- Parent resurrection one level deep, process_templates KeyError on
  geometry-less objects (from 20 Sept) — unchanged.
- Correction: the 2026-08-13 entry says `cityjson-writter-copy`; the branch
  is `cityjson-export`.



## 2026-09-20 — X3 done, round-trip green

- export() builds the subset: createCityJSON, copy version/transform, copy
  surviving CityObjects, then process_geometry / process_templates /
  process_appearance, then metadata. Mirrors get_subset_cotype.
- Guarded process_templates behind "geometry-templates" in citymodel, and
  dropped the empty `subset_cm["appearance"] = {}` line — process_appearance
  uses setdefault. Both are deliberate divergences from get_subset_cotype.
- prune_dangling_children: filters each surviving object's "children" down to
  surviving ids, deletes the key when empty. Only children — get_surviving_ids
  already resurrects parents, so a parents filter is dead code today.
- First round-trip assertion (only checked CityObjects keys) passed with
  vertices == []. Added `len(output["vertices"]) == 8` to make the test
  actually prove something.
- 256 passed.

Open gaps found while building this:
- deepcopy (X4) is now more urgent: prune deletes keys from CityObject dicts
  shared with self.citymodel, so export mutates the live model's structure,
  not just its indices.
- Parent resurrection in get_surviving_ids is one level deep — it loops a
  snapshot (`list(uids)`), so a resurrected parent's own parents are never
  walked. Building -> BuildingPart -> BuildingInstallation leaves a dangling
  "parents" ref. Fix transitively, or add the parents filter as a net.
- process_templates does j2["CityObjects"][each]["geometry"] with no .get() —
  KeyError on a CityObject with no geometry, which the spec allows.


## 2026-09-09 — Phase 1 done (C0.2, C1.1, C1.2, C1.3)

- Synced with upstream (now at v1.0.1). Merged writter + develop into
  cityjson-export, no conflicts.
- Built the fixture in tests/test_export.py: two Buildings, MultiSurface
  cubes, 16 quantized vertices, scale 0.001. Imports as 1 layer / 2 features.
- Round-trip test written and failing on purpose:
  ModuleNotFoundError: No module named 'core.exporting'. Committed red.
- API now pinned by its first caller: CityJSONExporter(layers, citymodel=...)
  .export() -> dict, and save_cityjson_model(dict, path).

Next: C2.1, the vertices writer — inverse of VerticesCache.


## 2026-08-13

Branch: `cityjson-writter-copy`

**Done**

- Branch set up off `cityjson-writter`; fork + local synced with upstream.
- Repo symlinked into the QGIS plugin dir — edits run live.
- Confirmed the export dialog loads on the post-restructure codebase. Was untested.

**Decided**

- Build on `cityjson-writter`: Gina merged `develop` into it on 7 Aug (`98d21c2`), so it's
  `develop` + 7 scaffold files. Verified — zero `develop` commits missing.
- One branch for the whole feature. The work is sequential (serializer needs
  `GeometryWriter`), so stacked branches would be overhead.
- Don't touch `Changelog.md` until PR — it's a release log, edits conflict on every release.

**Corrected**

- Single-polygon features aren't dropped by `SemanticSurfaceFeatureDecorator` — they land
  with **null geometry** (`setGeometry` never called).
- The `# TODO: This is wrong!` is about the dict value being a bare polygon instead of a
  geometry, not about the missing `semantic.values` index.

**Open**

- Is Gina still on `cityjson-writter`? Collision risk.
- Processing algorithm as well as the menu action?
- Are QGIS-authored new CityObjects in scope?
- `resources.py` generated but missing from `.gitignore`. Left for now.

**Next**

- Round-trip test as spec: import → delete one CityObject → export → re-import → assert
  only that object is gone.

---