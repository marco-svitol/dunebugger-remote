# Versioning and Release Guide

## Overview

This project uses automated semantic versioning and CI/CD workflows to manage releases and Docker image builds.

## Versioning System

### Semantic Versioning

The project follows [Semantic Versioning 2.0.0](https://semver.org/):
- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality additions
- **PATCH** version for backwards-compatible bug fixes

### Commit Message Convention

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

#### Commit Types and Version Impact

The version bump behavior differs between **stable** and **prerelease** branches:

##### On Stable Branches (`main`)

| Type | Description | Version Bump | Example |
|------|-------------|--------------|---------|
| `feat` | New feature | MINOR | `1.0.0` → `1.1.0` |
| `fix` | Bug fix | PATCH | `1.0.0` → `1.0.1` |
| `perf` | Performance improvement | PATCH | `1.0.0` → `1.0.1` |
| `docs` | Documentation changes | PATCH | `1.0.0` → `1.0.1` |
| `style` | Code style changes | PATCH | `1.0.0` → `1.0.1` |
| `refactor` | Code refactoring | PATCH | `1.0.0` → `1.0.1` |
| `test` | Test additions/changes | PATCH | `1.0.0` → `1.0.1` |
| `build` | Build system changes | PATCH | `1.0.0` → `1.0.1` |
| `ci` | CI/CD changes | PATCH | `1.0.0` → `1.0.1` |
| `chore` | Other changes | No release | - |
| `feat!` or `BREAKING CHANGE` | Breaking changes | MAJOR | `1.0.0` → `2.0.0` |

##### On Prerelease Branches (`develop`)

| Type | Description | Version Bump | Example |
|------|-------------|--------------|---------|
| `feat` | New feature | PRERELEASE | `1.0.0-beta.4` → `1.0.0-beta.5` |
| `fix` | Bug fix | PRERELEASE | `1.0.0-beta.4` → `1.0.0-beta.5` |
| `perf` | Performance improvement | PRERELEASE | `1.0.0-beta.4` → `1.0.0-beta.5` |
| Any other type | Any change triggering release | PRERELEASE | `1.0.0-beta.4` → `1.0.0-beta.5` |
| `chore` | Other changes | No release | - |

> **Note**: On prerelease branches, all commit types that trigger a release will increment the **prerelease number** (e.g., `beta.5` → `beta.6`) rather than the semantic version components (major/minor/patch). The accumulated changes will determine the proper version bump when merged to `main`.

#### Examples

**On `main` branch (stable releases):**
```bash
# Minor version bump: 1.0.0 → 1.1.0
feat: add NTP status monitoring

# Patch version bump: 1.0.0 → 1.0.1
fix: correct websocket connection handling

# Major version bump: 1.0.0 → 2.0.0
feat!: redesign message queue API

BREAKING CHANGE: The mqueue message format has changed.
All clients must update to the new format.

# No version bump
chore: update dependencies
```

**On `develop` branch (prerelease):**
```bash
# Prerelease bump: 1.0.0-beta.4 → 1.0.0-beta.5
feat: add NTP status monitoring

# Prerelease bump: 1.0.0-beta.5 → 1.0.0-beta.6
fix: correct websocket connection handling

# Prerelease bump: 1.0.0-beta.6 → 1.0.0-beta.7
feat!: redesign message queue API

# No version bump
chore: update dependencies
```

> **Important**: When `develop` is merged to `main`, all accumulated `feat`, `fix`, and breaking changes since the last stable release will determine the final version. For example, if `develop` has 3 `feat:` commits since `1.0.0`, merging to `main` will create `1.3.0`.

## Workflows

### 1. Semantic Release Workflow

**File**: `.github/workflows/semantic-release.yml`

**Triggers**:
- Push to `main` branch (production releases)
- Push to `develop` branch (beta pre-releases)

**What it does**:
1. Analyzes commit messages since last release
2. Determines next version number
3. Generates CHANGELOG.md
4. Creates Git tag (e.g., `v1.2.3` or `v1.2.3-beta.5`)
5. Creates GitHub release with release notes

**Branch Behavior**:
- **main**: Creates stable releases (e.g., `v1.2.3`)
- **develop**: Creates pre-releases (e.g., `v1.2.3-beta.1`)

**Note**: No VERSION file is created anymore. Git tags are the single source of truth.

### 2. Docker Build & Push Workflow

**File**: `.github/workflows/docker-build-push.yml`

**Triggers**:
- After successful semantic release
- Manual workflow dispatch

**Docker Image Tags**:

| Branch/Event | Tags Created | Example |
|--------------|--------------|---------|
| **main** | `latest`, `<version>`, `<version>-<commit>` | `latest`, `1.2.3`, `1.2.3-abc1234` |
| **develop** | `develop`, `<version>`, `<version>-<commit>` | `develop`, `1.2.3-beta.1`, `1.2.3-beta.1-abc1234` |

**Build Process**:
1. Checks out repository with full git history (`fetch-depth: 0`)
2. Extracts version from git tags during Docker build
3. Generates `_version_info.py` file in builder stage
4. Copies generated file to final image
5. No git or .git directory in final image (secure & minimal)

## Version Information in Application

### Version Storage and Retrieval

The application uses **git tags as the single source of truth** for version information. The version is handled differently in different environments:

#### In Docker Containers (Production)
1. During Docker build, version information is extracted from git tags using `git describe --tags`
2. A Python file `app/_version_info.py` is generated containing the version details
3. Git is removed from the final container image (security & size optimization)
4. At runtime, `version.py` reads from the pre-generated `_version_info.py` file

#### In Local Development
1. No `_version_info.py` file exists (it's in .gitignore)
2. `version.py` falls back to calling `git describe --tags` directly
3. Requires git to be installed locally (typically already available)

#### Fallback Behavior
If neither the generated file exists nor git is available, version defaults to `0.0.0-unknown`.

### Version Components

The version information consists of three components:

- **version**: Semantic version number (e.g., `1.0.0`)
- **build**: Build type/prerelease identifier (e.g., `beta.5`, `release`, `beta.5.dirty`)
- **commit**: Short git commit hash (e.g., `54b99d4`)

### Querying Version via Message Queue

Send a message with subject `get_version`:

```python
# Request
{
  "subject": "remote.command.get_version",
  "body": {}
}

# Response
{
  "subject": "remote.reply.version_info",
  "body": {
    "version": "1.2.3",
    "build": "prod",
    "commit": "abc1234",
    "full_version": "1.2.3-prod+abc1234"
  }
}
```

### Programmatic Access

```python
from version import get_version_info

# Get full version info
info = get_version_info()
# Returns: {
#   "version": "1.2.3",
#   "build": "prod",
#   "commit": "abc1234",
#   "full_version": "1.2.3-prod+abc1234"
# }
```

## Release Workflow

### For Feature Development

1. Create feature branch from `develop`:
   ```bash
   git checkout develop
   git pull
   git checkout -b feature/my-new-feature
   ```

2. Make changes and commit using conventional commits:
   ```bash
   git add .
   git commit -m "feat: add new awesome feature"
   ```

3. Push and create PR to `develop`:
   ```bash
   git push -u origin feature/my-new-feature
   ```

4. After PR is merged to `develop`:
   - Semantic Release creates a beta pre-release
   - Docker image is built with `develop` tag
   - Example: `marcosvitol/dunebugger-remote:develop`

### For Production Release

1. Create PR from `develop` to `main`

2. After PR is merged to `main`:
   - Semantic Release creates a production release
   - Docker image is built with `latest` and version tags
   - Example tags:
     - `marcosvitol/dunebugger-remote:latest`
     - `marcosvitol/dunebugger-remote:1.2.3`
     - `marcosvitol/dunebugger-remote:1.2.3-abc1234`

## Docker Image Usage

### Pull Latest Production Image
```bash
docker pull marcosvitol/dunebugger-remote:latest
```

### Pull Specific Version
```bash
docker pull marcosvitol/dunebugger-remote:1.2.3
```

### Pull Development Image
```bash
docker pull marcosvitol/dunebugger-remote:develop
```

### Check Version in Running Container
```bash
docker exec <container-name> python -c "from version import get_version_info; print(get_version_info())"
```

## Version Architecture Details

### Multi-Stage Docker Build

The Dockerfile uses a two-stage build process:

**Stage 1: Builder**
- Copies `.git` directory
- Installs git temporarily
- Runs `git describe --tags --always --dirty` to extract version
- Parses version components (version, build type, commit)
- Generates `app/_version_info.py` with hardcoded values
- Removes git and cleans up

**Stage 2: Runtime**
- Based on minimal Python image
- Copies generated `_version_info.py` from builder stage
- Copies application code
- **No git installed, no .git directory present**
- Minimal attack surface and smaller image size

### Version File Structure

Generated `_version_info.py` contains:
```python
# Auto-generated version file - DO NOT EDIT
# Generated at build time from git tags
__version__ = "1.0.0"
__build__ = "beta.5"
__commit__ = "54b99d4"
```

### Version Resolution Logic

The `version.py` module follows this priority:

1. **Try to load from `_version_info.py`** (Docker containers)
   - Fast, no external dependencies
   - Generated at build time

2. **Fall back to git** (Local development)
   - Runs `git describe --tags --always --dirty`
   - Parses output to extract components
   - Requires git installed locally

3. **Final fallback** (Neither available)
   - Returns `0.0.0-unknown+unknown`

## Initial Setup

### Required GitHub Secrets

Configure these secrets in your GitHub repository (Settings → Secrets and variables → Actions):

1. `DOCKER_HUB_USERNAME`: Your Docker Hub username
2. `DOCKER_HUB_ACCESS_TOKEN`: Docker Hub access token (create at hub.docker.com → Account Settings → Security)

### Repository Permissions

The semantic-release workflow needs write permissions:
- Go to Settings → Actions → General → Workflow permissions
- Select "Read and write permissions"
- Check "Allow GitHub Actions to create and approve pull requests"

## Troubleshooting

### Release Not Created

**Problem**: Commits pushed but no release created.

**Solution**: Ensure commits follow conventional commit format:
```bash
# ✅ Good - will trigger release
git commit -m "fix: correct typo in config"

# ❌ Bad - will not trigger release
git commit -m "fixed typo"
```

### Version Shows 0.0.0-unknown Locally

**Problem**: Running locally shows default version instead of actual version.

**Solution**: 
1. Ensure you have git installed
2. Ensure you're in a git repository with tags
3. Check that tags exist: `git tag -l`
4. If no tags, semantic-release will create them on next push to main/develop

### Version Shows Dirty Flag

**Problem**: Version shows `1.0.0-beta.5.dirty` instead of `1.0.0-beta.5`.

**Solution**: This is expected when you have uncommitted changes. Commit or stash changes:
```bash
git status  # See what's uncommitted
git add .
git commit -m "feat: my changes"
```

### Docker Build Fails on Version Extraction

**Problem**: Docker build fails in the version extraction stage.

**Solution**: 
1. Ensure git history is available: GitHub Actions must use `fetch-depth: 0`
2. Ensure at least one tag exists in the repository
3. Check Dockerfile builder stage logs for errors

## Manual Operations

### Check Current Version Locally
```bash
# Using git
git describe --tags --always

# Using Python
python3 -c "from app.version import get_version_info; print(get_version_info())"
```

### Create Manual Tag (if needed)
```bash
# Create annotated tag
git tag -a v1.2.3 -m "Release version 1.2.3"

# Push tag to trigger workflows
git push origin v1.2.3
```

### Build Docker Image Locally with Version
```bash
# Build with automatic version extraction
docker build -t dunebugger-remote:local .

# Check version in built image
docker run --rm dunebugger-remote:local python -c "from version import get_version_info; print(get_version_info())"
```

## References

- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [semantic-release](https://github.com/semantic-release/semantic-release)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
