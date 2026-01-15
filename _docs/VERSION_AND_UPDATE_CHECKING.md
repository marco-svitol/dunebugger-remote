# Version Management and Update Checking

## Problem Statement

The dunebugger project needed a robust version management system that:
1. Includes build numbers in both prerelease and release versions
2. Works with semantic-release automation in GitHub Actions
3. Allows local installations to check for updates from GitHub releases
4. Handles the discrepancy between local version info (with build numbers) and GitHub API responses (without build numbers)

## The Challenge

**Local Version Information:**
```json
{
  "version": "1.0.0",
  "prerelease": "beta.3",
  "build_number": 85,
  "commit": "c6e425e",
  "full_version": "1.0.0-beta.3.dev2"
}
```

**GitHub Releases API Response:**
```json
{
  "tag_name": "v1.0.0-beta.3",
  "name": "v1.0.0-beta.3",
  "prerelease": true
}
```

**The Problem:** How do we compare versions when the local system has detailed build information, but GitHub only provides the tag name?

## Solution Architecture

### 1. Enhanced Version Generation (`generate_version.sh`)

The version generation script was enhanced to include comprehensive version metadata:

**Key Features:**
- Parses git tags following semantic-release format (`v1.0.0-beta.3`)
- Calculates build number from total commit count
- Identifies build type: `release`, `prerelease`, `prerelease-dev`, `development`
- Handles dirty working directory and dev commits
- Generates structured JSON output

**Version File Structure:**
```json
{
  "version": "1.0.0",           // Base semantic version
  "prerelease": "beta.3",       // Prerelease identifier (null for releases)
  "build_type": "prerelease",   // Type of build
  "build_number": 85,           // Monotonically increasing build counter
  "commit": "c6e425e",          // Short commit hash
  "full_version": "1.0.0-beta.3" // Complete version string
}
```

**Version Construction Logic:**

| Git State | Build Type | Prerelease | Full Version |
|-----------|-----------|------------|--------------|
| `v1.0.0` (tagged) | `release` | `null` | `1.0.0` |
| `v1.0.0-beta.3` (tagged) | `prerelease` | `beta.3` | `1.0.0-beta.3` |
| `v1.0.0-beta.3-2-gc6e425e` | `prerelease-dev` | `beta.3` | `1.0.0-beta.3.dev2` |
| No tag, 5 commits | `development` | `null` | `0.0.0-dev5` |
| Any dirty state | (any) + `.dirty` | (any) | (any)`.dirty` |

### 2. Updated Application Version Module (`app/version.py`)

The version module was enhanced to expose all version metadata:

**Module-Level Variables:**
```python
__version__ = "1.0.0"           # Base version
__prerelease__ = "beta.3"       # Prerelease identifier
__build_type__ = "prerelease"   # Build type
__build_number__ = 85           # Build number
__commit__ = "c6e425e"          # Git commit
__full_version__ = "1.0.0-beta.3" # Full semantic version
```

**Features:**
- Reads VERSION file (primary source)
- Falls back to git commands if VERSION doesn't exist
- Maintains backward compatibility with old VERSION format
- Provides both simple (`__version__`) and detailed (`__full_version__`) strings

### 3. GitHub Actions Integration (`.github/workflows/semantic-release.yml`)

The CI/CD workflow was updated to include version metadata in releases:

**Key Changes:**

1. **Generate VERSION File After Release:**
   ```bash
   ./generate_version.sh
   ```
   This creates the VERSION file based on the tag just created by semantic-release.

2. **Package Application with VERSION:**
   ```bash
   tar czf "dunebugger-${VERSION}.tar.gz" \
     --exclude='.git*' \
     --exclude='node_modules' \
     --exclude='*.pyc' \
     --exclude='__pycache__' \
     --exclude='.pytest_cache' \
     --exclude='*.tar.gz' \
     .
   ```

3. **Upload VERSION.json as Standalone Asset:**
   ```bash
   cp VERSION "VERSION.json"
   ```
   This allows the update checker to download version info without extracting the tarball.

**Release Assets Structure:**
```
dunebugger-1.0.0-beta.3/
├── dunebugger-1.0.0-beta.3.tar.gz (contains VERSION file inside)
├── dunebugger-1.0.0-beta.3.tar.gz.sha256
└── VERSION.json (standalone, for update checking)
```

### 4. Update Checker Module (`app/update_checker.py`)

A new module was created to handle version comparison and update checking:

**Two-Tier Comparison Strategy:**

```
┌─────────────────────────────────────────┐
│  Check GitHub Releases API              │
│  GET /repos/{owner}/{repo}/releases     │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  Try to Download VERSION.json           │
│  (Available in new releases)            │
└─────────────────┬───────────────────────┘
                  │
        ┌─────────┴──────────┐
        │                    │
        ▼                    ▼
   ┌─────────┐        ┌──────────┐
   │ Success │        │ Not Found│
   └────┬────┘        └────┬─────┘
        │                  │
        │                  ▼
        │         ┌─────────────────┐
        │         │ Parse Tag Name  │
        │         │ (v1.0.0-beta.3) │
        │         └────┬────────────┘
        │              │
        └──────┬───────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  Compare Semantic Versions               │
│  (Ignore build numbers in comparison)   │
└──────────────┬───────────────────────────┘
               │
               ▼
        ┌──────────────┐
        │  local < remote? │
        └──────┬─────────┘
               │
        ┌──────┴──────┐
        ▼             ▼
   ┌────────┐    ┌────────┐
   │ UPDATE │    │ Check  │
   │AVAILABLE│   │ Builds │
   └────────┘    └────┬───┘
                      │
              ┌───────┴────────┐
              ▼                ▼
        ┌──────────┐     ┌──────────┐
        │local_build<   │ UP TO    │
        │remote_build?  │ DATE     │
        └──────┬───┘     └──────────┘
               │
               ▼
        ┌──────────┐
        │  UPDATE  │
        │AVAILABLE │
        └──────────┘
```

**Version Comparison Logic:**

```python
def parse_semver(version_string):
    """
    Parse semantic version into comparable tuple.
    
    Examples:
        "1.0.0"         -> (1, 0, 0, None)
        "1.0.0-beta.3"  -> (1, 0, 0, "beta.3")
        "2.1.5-alpha.1" -> (2, 1, 5, "alpha.1")
    
    Comparison rules:
        - Release versions > prerelease versions
        - 1.0.0 > 1.0.0-beta.3
        - 1.0.0-beta.3 > 1.0.0-beta.2
    """
    # Implementation follows PEP 440 / SemVer 2.0 rules
```

**Key Decision:** Build numbers are NOT used for version comparison, only for tracking:
- ✅ Semantic version determines if update is available
- ✅ Build numbers only break ties if semantic versions are identical
- ✅ This matches semantic-release behavior (doesn't include builds in tags)

### 5. Example and Documentation

**Version Comparison Demo (`examples/version_comparison_demo.py`):**

Demonstrates all comparison scenarios:

```
Scenario 1: New prerelease available
----------------------------------------------------------------------
  Local:  1.0.0-beta.2         (build #79)
  Remote: 1.0.0-beta.3         (build #0)
  Result: ✅ UPDATE AVAILABLE - Remote is newer

Scenario 2: Release available (upgrading from prerelease)
----------------------------------------------------------------------
  Local:  1.0.0-beta.3         (build #85)
  Remote: 1.0.0                (build #0)
  Result: ✅ UPDATE AVAILABLE - Remote is newer

Scenario 3: Already on latest
----------------------------------------------------------------------
  Local:  1.0.0-beta.3         (build #85)
  Remote: 1.0.0-beta.3         (build #0)
  Result: ✓ UP TO DATE - Versions match

Scenario 4: Local is newer (dev build ahead of release)
----------------------------------------------------------------------
  Local:  1.0.1                (build #95)
  Remote: 1.0.0                (build #0)
  Result: ⚠️  LOCAL IS NEWER - Remote is older

Scenario 5: Same version, different build
----------------------------------------------------------------------
  Local:  1.0.0-beta.3         (build #85)
  Remote: 1.0.0-beta.3         (build #90)
  Result: ✅ UPDATE AVAILABLE - Same version, newer build
```

## Usage Examples

### Checking for Updates

```python
from app.update_checker import UpdateChecker

# Initialize checker
checker = UpdateChecker(
    github_account="marco-svitol",
    repo_name="dunebugger"
)

# Check for updates (releases only)
result = checker.check_for_updates(include_prereleases=False)

# Check for updates (including prereleases)
result = checker.check_for_updates(include_prereleases=True)

# Handle result
if result['has_update']:
    print(f"Update available: {result['remote_version']['full_version']}")
    print(f"Current version: {result['local_version']['full_version']}")
    print(f"Download URL: {result['download_url']}")
    print(f"Release notes: {result['release_notes']}")
else:
    print("You're up to date!")
```

### Getting Version Information

```python
from app import version

# Simple version
print(version.__version__)        # "1.0.0"

# Full semantic version
print(version.__full_version__)   # "1.0.0-beta.3"

# Detailed information
print(version.__build_number__)   # 85
print(version.__build_type__)     # "prerelease"
print(version.__commit__)         # "c6e425e"
print(version.__prerelease__)     # "beta.3"
```

## Files Modified/Created

### Modified Files

1. **`generate_version.sh`**
   - Added build_number calculation
   - Added prerelease field extraction
   - Added build_type classification
   - Added full_version construction
   - Improved git tag parsing

2. **`app/version.py`**
   - Added support for new VERSION file format
   - Exposed all version metadata as module variables
   - Maintained backward compatibility
   - Improved git fallback handling

3. **`.github/workflows/semantic-release.yml`**
   - Added VERSION file generation step
   - Added VERSION.json standalone asset upload
   - Added tarball artifact creation with VERSION included
   - Added SHA256 checksum generation

### New Files

1. **`app/update_checker.py`**
   - Complete update checking logic
   - GitHub API integration
   - VERSION.json download and parsing
   - Semantic version comparison
   - Result formatting

2. **`examples/version_comparison_demo.py`**
   - Demonstrates all comparison scenarios
   - Shows decision logic
   - Provides insights on versioning strategy

3. **`docs/VERSION_AND_UPDATE_CHECKING.md`** (this file)
   - Complete documentation
   - Architecture explanation
   - Usage examples

## Benefits

### For Developers
- ✅ Build numbers tracked in all builds (local and CI)
- ✅ Easy identification of exact build in production
- ✅ Git fallback for development without VERSION file
- ✅ Backward compatible with old VERSION format

### For CI/CD
- ✅ Semantic-release workflow unchanged
- ✅ Version metadata automatically included in releases
- ✅ Artifacts traceable to specific commits
- ✅ SHA256 checksums for integrity verification

### For Users
- ✅ Automatic update checking
- ✅ Choice between stable and prerelease channels
- ✅ Direct download links to latest versions
- ✅ Release notes displayed with updates

### For Update Logic
- ✅ Semantic version comparison (standard-compliant)
- ✅ Build numbers don't interfere with version precedence
- ✅ Handles missing VERSION.json (backward compatible)
- ✅ Prerelease vs release comparison works correctly

## Version Precedence Rules

Following SemVer 2.0 specification:

```
0.0.0-dev5          < (development build)
1.0.0-alpha.1       < (alpha prerelease)
1.0.0-beta.1        < (beta prerelease)
1.0.0-beta.2        < (newer beta)
1.0.0-rc.1          < (release candidate)
1.0.0               < (release)
1.0.1               < (patch release)
1.1.0               < (minor release)
2.0.0                 (major release)
```

## Future Enhancements

1. **Automatic Updates**: Add option to download and install updates automatically
2. **Update Notifications**: Desktop notifications when updates are available
3. **Rollback Support**: Keep previous versions for rollback capability
4. **Delta Updates**: Download only changed files instead of full tarball
5. **Update Scheduling**: Allow users to configure update check frequency
6. **Mirror Support**: Add support for alternative download mirrors

## Conclusion

This solution provides a comprehensive version management and update checking system that:
- Integrates seamlessly with semantic-release
- Tracks detailed build information locally
- Enables reliable update checking despite GitHub API limitations
- Follows semantic versioning best practices
- Maintains backward compatibility
- Provides excellent developer and user experience

The two-tier comparison strategy (semantic version first, build number as tiebreaker) ensures that version precedence follows standards while still leveraging build numbers for precise tracking.