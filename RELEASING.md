# Releasing the CityJSON Loader

How to make a new release.


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

### 4. Merge to main

```sh
# Merge the release branch into develop
git checkout develop
git merge version-<version>
git push origin develop

# Merge develop into main and tag the release there
git checkout main
git merge develop
```

### 5. Build the package

```sh
make package VERSION=v<version>
```

This creates `CityJSON-loader.zip` from the tag using `git archive`.

### 6. Upload to the QGIS repository

```sh
make upload
```

This uses `scripts/plugin_upload.py` (XML-RPC) and prompts for your
<https://plugins.qgis.org> username/password.

Alternatively, upload `CityJSON-loader.zip` manually via
<https://plugins.qgis.org/plugins/>.

And wait for approval.

### 7. Tag and release

On main create new tag and push it:

```bash
git tag v<version>
git push origin main --tags
```
Then go to the tag on the repo and create a release. Finally edit the release to upload the .zip file to it. 

### 8. Verify

Install the plugin from the repository in a fresh QGIS profile and do a smoke
test (load a CityJSON file, check the processing toolbox entry).

## Notes

- `qgis-plugin-ci` (see `requirements.txt`) can also be used for packaging and
  releasing; it reads `metadata.txt` and a changelog file. The Makefile
  targets above are the currently documented flow.
- Keep the changelog entry short and descriptive — it is the release notes shown
  to users.
