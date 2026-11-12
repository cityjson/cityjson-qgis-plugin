# CityJSON export

For the full history of decisions, see `docs/export-development-log.md`.

## What it does

Load a CityJSON file into QGIS, edit it, and save it back as a new CityJSON file.

Supported edits:

- delete objects
- change attributes
- keep or drop LoDs that were not loaded
- export only an area (bounding box)

Not supported:

- **geometry edits** — export refuses and names the edited objects
- new objects drawn in QGIS
- deleting a single semantic surface of an object

Everything that is not touched is kept as in the original file: Solids, semantic surfaces,
appearances, geometry templates, unloaded LoDs, metadata.

## How to use it

**Menu:** Vector → CityJSON Loader → Export CityJSON...

1. Pick the loaded file from the dropdown.
2. Pick where to save.
3. Optional: draw an area, untick "Keep LoDs and objects that weren't loaded", tick "Add saved
   file to map".
4. Click Convert.

The dialog knows which file the layers came from and how they were loaded. So no need to enter
that again.

**Processing:** Toolbox → CityJSON Loader → Export → Export CityJSON. Same export, but requires the
original file path, loaded LoD and semantic-surfaces setting as inputs.

## How it works

Export does not rebuild CityJSON from the QGIS layers. It starts from the original file and
applies only the changes:

1. Read the original file again (path stored on the layer).
2. Find which objects still have rows in QGIS. No row = deleted.
3. Copy the surviving objects from the original, untouched.
4. Apply attribute edits.
5. Drop unloaded LoDs, or objects outside the area, if asked.
6. Renumber vertices, materials and textures (reuses `core/subset.py`).
7. Write the file.

Copying from the original is why Solids, appearances and templates survive: QGIS layers are
flat `MultiPolygonZ` and lose that structure.

## Code structure

| File | What |
|---|---|
| `core/exporting.py` | `CityJSONExporter`, `read_provenance`, `save_cityjson_model` |
| `core/loading.py` | passes load settings to the layer manager |
| `core/layers.py` | `DynamicLayerManager` stamps each layer |
| `cityjson_loader.py` | menu dialog: `write()`, `export_cityjson()` |
| `gui/cityjson_writer_dialog.py` + `.ui` | the dialog |
| `processing/cityjson_export_algorithm.py` | Processing algorithm |
| `scripts/check_geometry.py` | finds non-planar, degenerate, self-intersecting faces |

### Layer stamps

At load time each layer gets these custom properties:

| Key | Value |
|---|---|
| `cityjson/source` | full path of the original file |
| `cityjson/load_id` | one id per load; groups layers from the same load |
| `cityjson/lod` | loaded LoD (JSON string) |
| `cityjson/semantic_surfaces` | `true` / `false` |
| `cityjson/keep_parent_attributes` | `true` / `false` |

## Rules and key decisions

- **One object, many rows.** With LoD or semantic-surface splitting, one object becomes several
  rows. The object survives if any of its LoD rows survive. Deleting only some of its surface rows
  is refused.
- **Never-loaded objects.** If one LoD is loaded, objects without that LoD never appear in QGIS.
  They are kept by default, not treated as deleted.
- **Geometry is read-only.** Each row's geometry is compared with the original, corner by corner,
  within half a grid step. Any difference stops the export. Reason: QGIS stores a shared corner
  as separate copies, one per face, so moving one breaks the building (measured, see the log).
- **Area filter** keeps objects whose centre is inside the box, plus their parents and children —
  the same rule as the area filter when loading.

## Limits

- **One QGIS session.** Saving and reopening the project keeps the stamps but empties the layers.
  Menu export refuses empty layers; load the file again.
- **"Inherit parent attributes"** loads are refused (parent values would be saved into children).
- Output is plain CityJSON, not CityJSONSeq.

## Testing

```powershell
docker build -f docker/Dockerfile.qgis-3.40 -t cityjson-qgis-plugin-test-340 .   # once
docker run --rm -v "${PWD}:/app" cityjson-qgis-plugin-test-340
```

Export tests: `tests/test_export.py`, `tests/test_export_algorithm.py`,
`tests/test_check_geometry.py`. Dialog tests: `tests/test_cityjson_writer_dialog.py` (the
window) and `TestExportDialog` in `tests/test_cityjson_loader.py` (the Convert button).

Validate exported files with cjval: https://validator.cityjson.org