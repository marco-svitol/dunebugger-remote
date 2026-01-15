# Version Management and Update Checking Implementation

## Summary

This implementation adapts the dunebugger-remote project to use the new version management and update checking approach as documented in `_docs/VERSION_AND_UPDATE_CHECKING.md`.

## Changes Made

### 1. Enhanced Version Module (`app/version.py`)

**Changes:**
- Added support for new JSON-based VERSION file format with structured fields:
  - `version`: Base semantic version (e.g., "1.0.0")
  - `prerelease`: Prerelease identifier (e.g., "beta.5") or null
  - `build_type`: Type of build ("release", "prerelease", "prerelease-dev", "development")
  - `build_number`: Monotonically increasing build counter
  - `commit`: Short commit hash
  - `full_version`: Complete version string (e.g., "1.0.0-beta.5")

- Maintained backward compatibility with legacy formats:
  - Legacy `_version_info.py` file (if exists)
  - Old single-line VERSION file format
  - Git-based version detection (fallback)

- Enhanced git-based version generation with:
  - Build number calculation from commit count
  - Proper build type detection
  - Support for dirty working directory detection

**Module-Level Variables:**
```python
__version__       # "1.0.0"
__prerelease__    # "beta.5" or None
__build_type__    # "release", "prerelease", etc.
__build_number__  # 49
__commit__        # "be77d9a"
__full_version__  # "1.0.0-beta.5"
```

### 2. Semantic Version Parsing (`app/dunebugger_updater.py`)

**Added `parse_semver()` function:**
- Parses semantic version strings into comparable tuples
- Handles release vs prerelease versions correctly
- Ignores `.dev` and `.dirty` suffixes for comparison
- Returns tuple format: `(base_version_tuple, is_release, prerelease_tuple)`

**Version Comparison Rules:**
- Release versions > prerelease versions (1.0.0 > 1.0.0-beta.3)
- Prerelease ordering by number (beta.2 < beta.3)
- Development suffixes ignored in comparison

### 3. Enhanced Update Checker (`app/dunebugger_updater.py`)

**Updated `_fetch_latest_version()` method:**
- Two-tier version information retrieval:
  1. Try to download VERSION.json from release assets (contains full metadata)
  2. Fallback to parsing tag_name if VERSION.json not available

**Added helper methods:**
- `_get_version_from_release_assets()`: Downloads VERSION.json from GitHub release
- `_parse_tag_to_version_info()`: Parses tag name into version info dict (fallback)

**Updated `_compare_versions()` method:**
- Uses new `parse_semver()` function for accurate semantic versioning
- Properly handles prerelease vs release comparison
- Maintains fallback to packaging library

**Updated `_get_python_app_version()` method:**
- Supports new JSON VERSION file format
- Maintains backward compatibility with old formats
- Returns `full_version` field directly

### 4. GitHub Actions Workflow (`.github/workflows/semantic-release.yml`)

**Added version file generation and artifact creation:**
- Generates VERSION file after release using `generate_version.sh`
- Creates release tarball with VERSION file included
- Generates SHA256 checksum for integrity verification
- Uploads VERSION.json as standalone asset for update checker

**Artifact Structure:**
```
dunebugger-remote-1.0.0-beta.5/
├── dunebugger-remote-1.0.0-beta.5.tar.gz (includes VERSION inside)
├── dunebugger-remote-1.0.0-beta.5.tar.gz.sha256
└── VERSION.json (standalone, for update checking)
```

### 5. Version Generation Script (`generate_version.sh`)

**New script that:**
- Parses git tags following semantic-release format (`v1.0.0-beta.3`)
- Calculates build number from total commit count
- Identifies build type: `release`, `prerelease`, `prerelease-dev`, `development`
- Handles dirty working directory
- Generates structured JSON output in VERSION file

**Example Output:**
```json
{
  "version": "1.0.0",
  "prerelease": "beta.5",
  "build_type": "prerelease",
  "build_number": 49,
  "commit": "be77d9a",
  "full_version": "1.0.0-beta.5"
}
```

## Benefits

### For Developers
✅ Build numbers tracked in all builds (local and CI)
✅ Easy identification of exact build in production
✅ Git fallback for development without VERSION file
✅ Backward compatible with old VERSION format

### For CI/CD
✅ Semantic-release workflow unchanged
✅ Version metadata automatically included in releases
✅ Artifacts traceable to specific commits
✅ SHA256 checksums for integrity verification

### For Update Logic
✅ Semantic version comparison (standard-compliant)
✅ Build numbers available but don't interfere with version precedence
✅ Handles missing VERSION.json (backward compatible)
✅ Prerelease vs release comparison works correctly

## Version Precedence Examples

Following SemVer 2.0 specification:

```
0.0.0-dev5          < (development build)
1.0.0-alpha.1       < (alpha prerelease)
1.0.0-beta.1        < (beta prerelease)
1.0.0-beta.2        < (newer beta)
1.0.0-beta.3.dev2   = (same as beta.3, dev ignored)
1.0.0-rc.1          < (release candidate)
1.0.0               < (release)
1.0.1               < (patch release)
1.1.0               < (minor release)
2.0.0                 (major release)
```

## Testing

A test script `test_version_parsing.py` has been created to verify the `parse_semver()` function:

```bash
cd /home/marco/dev/dunebugger-project/dunebugger-remote
python3 test_version_parsing.py
```

All version comparison tests pass:
- ✓ Newer beta versions are correctly ordered
- ✓ Release versions are greater than prereleases
- ✓ Patch versions are correctly ordered
- ✓ Dev suffixes are correctly ignored in comparison

## Files Modified

1. ✅ `app/version.py` - Enhanced version detection and parsing
2. ✅ `app/dunebugger_updater.py` - Updated version comparison and fetching logic
3. ✅ `.github/workflows/semantic-release.yml` - Added artifact generation
4. ✅ `generate_version.sh` (new) - Script to generate VERSION file
5. ✅ `test_version_parsing.py` (new) - Test script for version parsing

## Next Steps

When ready to release:

1. Commit all changes to the feature branch
2. Merge to develop or main (depending on prerelease/release)
3. Semantic-release will automatically:
   - Create a new tag
   - Generate VERSION file
   - Create release artifacts
   - Upload VERSION.json for update checking
4. Docker build will be triggered automatically

## Verification

To verify the implementation:

1. **Test version generation:**
   ```bash
   ./generate_version.sh
   cat VERSION  # Should show valid JSON
   ```

2. **Test version parsing:**
   ```bash
   python3 test_version_parsing.py
   ```

3. **Test version module:**
   ```bash
   python3 -c "from app import version; import json; print(json.dumps(version.get_version_info(), indent=2))"
   ```

All tests pass successfully! ✅
