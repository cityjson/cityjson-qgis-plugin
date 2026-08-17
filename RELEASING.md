# Releasing the CityJSON Loader

This document describes how to cut a new release of the CityJSON Loader QGIS
plugin and publish it to the official QGIS plugin repository.

## Overview

A release consists of:

1. Updating the changelog and version.
2. Running the full test suite (lint, type check, tests).
3. Merging the release branch into `develop`, then into `main`, and tagging.
4. Building a zip package.
5. Uploading the package to <https://plugins.qgis.org>.

## Branching model

- `main` — the stable branch; reflects the latest released code.
- `develop` — the integration branch; feature and bugfix branches are merged
  here via pull request.

Release work happens on a feature branch (e.g. `version-<version>`). The flow:

1. Merge the feature branch into `develop` once it is reviewed and all tests
   pass.
2. When you are ready to release, merge `develop` into `main` and tag the
   release commit on `main`.

`develop` is merged into `main` **only** at release time; day-to-day work
always lands on `develop` first.

## Prerequisites

- Python 3.10+ and a recent QGIS installation (for local testing).
- Docker (for testing against specific QGIS versions).
- Credentials (username/password) for <https://plugins.qgis.org>.
- Push access to <https://github.com/cityjson/cityjson-qgis-plugin>.

## Step-by-step

### 1. Update the changelog

Edit `Changelog.md` and add a new section at the top, e.g.:

```md
## 1.2.0 - 2026-08-17

### Added
- ...

### Changed
- ...

### Fixed
- ...
```

Keep it concise and user-facing; this text is shown on the plugin page.

### 2. Bump the version

Update the `version` field in `metadata.txt` to match the changelog entry.

### 3. Run the checks and tests

All of the following must pass before tagging:

```sh
# Lint + format (ruff v0.8.4)
make format

# Type checking (mypy)
mypy

# Tests against each supported QGIS version (Docker)
make test-340
make test-344
make test-40
make test-42

# Or, run locally against your installed QGIS (uses QGIS_PYTHON from .env)
make test
```

On Apple Silicon, prefix the Docker targets with
`DOCKER_DEFAULT_PLATFORM=linux/amd64`.

### 4. Merge and tag

```sh
# Commit the changelog and version bump on the release branch
git add Changelog.md metadata.txt
git commit -m "Release <version>"

# Merge the release branch into develop
git checkout develop
git merge version-<version>
git push origin develop

# Merge develop into main and tag the release there
git checkout main
git merge develop
git tag v<version>
git push origin main --tags
```

### 5. Build the package

```sh
make zip
```

This creates `CityJSON-loader.zip` containing only the plugin files
(`PY_FILES`, `UI_FILES`, `EXTRAS` and `LICENSE`).

> `make package VERSION=v<version>` also exists but uses `git archive`, which
> includes development files (tests, CI config, etc.). Prefer `make zip` for a
> release.

### 6. Upload to the QGIS repository

```sh
make upload
```

This uses `scripts/plugin_upload.py` (XML-RPC) and prompts for your
<https://plugins.qgis.org> username/password.

Alternatively, upload `CityJSON-loader.zip` manually via
<https://plugins.qgis.org/plugins/>.

### 7. Verify

Install the plugin from the repository in a fresh QGIS profile and do a smoke
test (load a CityJSON file, check the processing toolbox entry).

## Notes

- `qgis-plugin-ci` (see `requirements.txt`) can also be used for packaging and
  releasing; it reads `metadata.txt` and a changelog file. The Makefile
  targets above are the currently documented flow.
- Keep the changelog entry short and descriptive — it is the release notes shown
  to users.
