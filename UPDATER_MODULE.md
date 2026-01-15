# Component Updater Module

## Overview

The Component Updater module is responsible for managing version tracking and automated updates for all DuneBugger components. It provides a centralized, secure, and reliable way to keep the system up-to-date.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DuneBugger Remote                             │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │              ComponentUpdater                                   │ │
│  │                                                                  │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │ │
│  │  │    Core      │  │  Scheduler   │  │    Remote    │         │ │
│  │  │  (Python)    │  │ (Container)  │  │ (Container)  │         │ │
│  │  │              │  │              │  │              │         │ │
│  │  │ Current: 1.0 │  │ Current: 1.0 │  │ Current: 1.0 │         │ │
│  │  │ Latest:  1.1 │  │ Latest:  1.1 │  │ Latest:  1.1 │         │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘         │ │
│  │                                                                  │ │
│  │  Periodic Check (24h)  ────────────────┐                        │ │
│  │  Manual Check (WebSocket) ─────────────┤                        │ │
│  │                                         │                        │ │
│  └─────────────────────────────────────────┼────────────────────────┘ │
│                                             │                          │
└─────────────────────────────────────────────┼──────────────────────────┘
                                              │
                                              ▼
                        ┌──────────────────────────────────┐
                        │      GitHub Repositories         │
                        │                                  │
                        │  • marco-svitol/dunebugger       │
                        │  • marco-svitol/dunebugger-...   │
                        │  • marco-svitol/dunebugger-...   │
                        │                                  │
                        │  Releases with:                  │
                        │  - Version tags                  │
                        │  - Release artifacts             │
                        │  - Update manifests (optional)   │
                        └──────────────────────────────────┘
```

## Update Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Update Procedure                             │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  │
                         ┌────────▼─────────┐
                         │  Check Updates   │
                         │  (Manual/Auto)   │
                         └────────┬─────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
           ┌────────▼──────────┐      ┌────────▼──────────┐
           │  GitHub API Call  │      │  Compare Versions │
           │  /releases/latest │      │  (Semantic Ver)   │
           └────────┬──────────┘      └────────┬──────────┘
                    │                           │
                    └─────────────┬─────────────┘
                                  │
                         ┌────────▼──────────┐
                         │  Update Available?│
                         └────────┬──────────┘
                                  │
                         ┌────────▼────────┐
                         │   Yes  │   No   │
                         └────┬───┴────┬───┘
                              │        │
                              │        └──────► End
                              │
                    ┌─────────▼──────────┐
                    │  User Triggers     │
                    │  Update (WebSocket)│
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Fetch Update      │
                    │  Manifest (if any) │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Pre-Update Checks │
                    │  • Disk space      │
                    │  • Backups         │
                    │  • Dependencies    │
                    └─────────┬──────────┘
                              │
                              ├─── Fail ──► End (Report Error)
                              │
                              Pass
                              │
              ┌───────────────┴───────────────┐
              │                               │
    ┌─────────▼──────────┐        ┌──────────▼─────────┐
    │  Python App Update │        │  Container Update  │
    │  (Core)            │        │  (Scheduler/Remote)│
    │                    │        │                    │
    │  1. Download .tar  │        │  1. Backup compose │
    │  2. Backup current │        │  2. Update image   │
    │  3. Stop service   │        │     tag in compose │
    │  4. Extract new    │        │  3. docker-compose │
    │  5. Install deps   │        │     pull <service> │
    │  6. Start service  │        │  4. docker-compose │
    │                    │        │     up -d <service>│
    └─────────┬──────────┘        └──────────┬─────────┘
              │                               │
              └───────────────┬───────────────┘
                              │
                    ┌─────────▼──────────┐
                    │ Post-Update Checks │
                    │  • Health endpoint │
                    │  • Service running │
                    │  • Container up    │
                    └─────────┬──────────┘
                              │
                              ├─── Pass ──► ┌─────────────┐
                              │              │   Success   │
                              │              │Update Version│
                              │              └─────────────┘
                              │
                              Fail
                              │
                    ┌─────────▼──────────┐
                    │     Rollback       │
                    │  • Restore backup  │
                    │  • Restart service │
                    │  • Report failure  │
                    └────────────────────┘
```

## Components Managed

The updater manages three components:

1. **dunebugger-core** (`core`)
   - Type: Python application
   - Distribution: GitHub Releases (tar.gz artifacts)
   - Installation: Direct file system deployment
   - Service: systemd service (`dunebugger`)

2. **dunebugger-scheduler** (`scheduler`)
   - Type: Docker container
   - Distribution: GHCR (GitHub Container Registry)
   - Installation: docker-compose
   - Service: Docker container

3. **dunebugger-remote** (`remote`)
   - Type: Docker container
   - Distribution: GHCR (GitHub Container Registry)
   - Installation: docker-compose
   - Service: Docker container (self)

## Configuration

Add the following section to `config/dunebugger.conf`:

```ini
[Updater]
updateCheckIntervalHours = 24
dockerComposePath = /opt/dunebugger/docker-compose.yml
coreInstallPath = /opt/dunebugger/core
backupPath = /opt/dunebugger/backups
```

### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `updateCheckIntervalHours` | int | 24 | Hours between automatic update checks |
| `dockerComposePath` | string | `/opt/dunebugger/docker-compose.yml` | Path to docker-compose file |
| `coreInstallPath` | string | `/opt/dunebugger/core` | Installation directory for core |
| `backupPath` | string | `/opt/dunebugger/backups` | Directory for backups |

## WebSocket API

### Check for Updates

**Subject:** `updater.check_updates`

**Request:**
```json
{
  "subject": "updater.check_updates",
  "source": "frontend",
  "body": {
    "force": true
  }
}
```

**Response:**
```json
{
  "subject": "update_check_result",
  "source": "controller",
  "body": {
    "components": {
      "core": {
        "current": "1.0.0",
        "latest": "1.1.0",
        "update_available": true,
        "release_notes": "### New Features\n- Feature 1\n- Feature 2",
        "last_checked": "2026-01-13T10:30:00"
      },
      "scheduler": {
        "current": "1.0.0",
        "latest": "1.0.0",
        "update_available": false,
        "release_notes": null,
        "last_checked": "2026-01-13T10:30:00"
      },
      "remote": {
        "current": "1.0.0",
        "latest": "1.1.0",
        "update_available": true,
        "release_notes": "### Bug Fixes\n- Fix 1",
        "last_checked": "2026-01-13T10:30:00"
      }
    }
  }
}
```

### Perform Update

**Subject:** `updater.perform_update`

**Request:**
```json
{
  "subject": "updater.perform_update",
  "source": "frontend",
  "body": {
    "component": "core",
    "dry_run": false
  }
}
```

**Response:**
```json
{
  "subject": "update_result",
  "source": "controller",
  "body": {
    "component": "core",
    "success": true,
    "message": "Updated core to 1.1.0",
    "dry_run": false
  }
}
```

## Update Manifests

Each component repository should include an `update-manifest.yaml` file at the root level, tagged with the release version. This manifest provides structured update instructions.

### Manifest for Containerized Components (Scheduler/Remote)

**File:** `update-manifest.yaml` (in repository root)

```yaml
version: "1.1.0"
component_type: "container"

# Minimum version of remote component required to perform this update
min_remote_version: "1.0.0"

# Pre-update validation checks
pre_update_checks:
  - type: "disk_space"
    minimum_mb: 500
    description: "Ensure sufficient disk space for new image"
  
  - type: "backup_exists"
    max_age_hours: 24
    description: "Verify recent backup exists"

# Update execution steps (informational - actual steps are in updater)
update_steps:
  - action: "backup_compose"
    description: "Backup current docker-compose.yaml"
  
  - action: "update_compose"
    service: "scheduler"
    image_tag: "1.1.0"
    description: "Update image tag in docker-compose"
  
  - action: "pull_image"
    image: "ghcr.io/marco-svitol/dunebugger-scheduler:1.1.0"
    description: "Pull new container image"
  
  - action: "restart_service"
    service: "scheduler"
    timeout_seconds: 30
    description: "Restart the service"

# Post-update validation
post_update_checks:
  - type: "container_running"
    container_name: "scheduler"
    description: "Verify container is running"
  
  - type: "health_endpoint"
    url: "http://localhost:8080/health"
    timeout_seconds: 60
    expected_status: 200
    description: "Check health endpoint responds"

# Rollback procedure if update fails
rollback_steps:
  - action: "restore_compose"
    description: "Restore docker-compose from backup"
  
  - action: "restart_service"
    service: "scheduler"
    description: "Restart with old version"
```

### Manifest for Python Application (Core)

**File:** `update-manifest.yaml` (in repository root)

```yaml
version: "1.2.0"
component_type: "python_app"

# Minimum version of remote component required to perform this update
min_remote_version: "1.0.0"

# Pre-update validation checks
pre_update_checks:
  - type: "disk_space"
    minimum_mb: 1000
    description: "Ensure sufficient disk space"
  
  - type: "service_running"
    service_name: "dunebugger"
    description: "Verify service is accessible before update"

# Update execution steps
update_steps:
  - action: "download_artifact"
    url: "https://github.com/marco-svitol/dunebugger/releases/download/v1.2.0/dunebugger-1.2.0.tar.gz"
    checksum: "sha256:abc123..."
    description: "Download release artifact"
  
  - action: "backup_installation"
    source: "/opt/dunebugger/core"
    destination: "/opt/dunebugger/backups/core.TIMESTAMP.tar.gz"
    description: "Backup current installation"
  
  - action: "stop_service"
    service_name: "dunebugger"
    description: "Stop the service"
  
  - action: "extract_artifact"
    archive: "dunebugger-1.2.0.tar.gz"
    destination: "/opt/dunebugger/core"
    description: "Extract new version"
  
  - action: "install_requirements"
    requirements_file: "/opt/dunebugger/core/requirements.txt"
    description: "Install Python dependencies"
  
  - action: "run_migrations"
    script: "/opt/dunebugger/core/scripts/migrate.sh"
    optional: true
    description: "Run database migrations if needed"
  
  - action: "start_service"
    service_name: "dunebugger"
    description: "Start the service"

# Post-update validation
post_update_checks:
  - type: "service_active"
    service_name: "dunebugger"
    timeout_seconds: 30
    description: "Verify service started successfully"
  
  - type: "health_endpoint"
    url: "http://localhost:5000/health"
    timeout_seconds: 60
    expected_status: 200
    description: "Check application health"
  
  - type: "version_check"
    expected_version: "1.2.0"
    description: "Verify correct version is running"

# Rollback procedure
rollback_steps:
  - action: "stop_service"
    service_name: "dunebugger"
    description: "Stop current version"
  
  - action: "restore_backup"
    source: "latest_backup"
    destination: "/opt/dunebugger/core"
    description: "Restore from backup"
  
  - action: "start_service"
    service_name: "dunebugger"
    description: "Start previous version"
```

## Usage Examples

### Programmatic Usage

```python
from dunebugger_updater import ComponentUpdater
from dunebugger_settings import settings

# Initialize updater
updater = ComponentUpdater(settings)

# Check for updates (manual)
results = await updater.check_updates(force=True)
for component, info in results.items():
    if info.update_available:
        print(f"{component}: {info.current_version} -> {info.latest_version}")

# Perform update with dry run
result = await updater.update_component('core', dry_run=True)
print(result)

# Perform actual update
result = await updater.update_component('scheduler', dry_run=False)
if result['success']:
    print(f"Update successful: {result['message']}")
else:
    print(f"Update failed: {result['message']}")

# Get all version information
versions = updater.get_all_versions()
```

### WebSocket Example (JavaScript)

```javascript
// Check for updates
websocket.send(JSON.stringify({
  subject: "updater.check_updates",
  source: "frontend",
  body: {
    force: true
  }
}));

// Listen for results
websocket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.subject === "update_check_result") {
    const components = data.body.components;
    
    Object.entries(components).forEach(([name, info]) => {
      if (info.update_available) {
        console.log(`${name}: Update available ${info.current} -> ${info.latest}`);
        
        // Show update button
        showUpdateButton(name, info);
      }
    });
  }
  
  if (data.subject === "update_result") {
    if (data.body.success) {
      console.log(`Update successful: ${data.body.message}`);
    } else {
      console.error(`Update failed: ${data.body.message}`);
    }
  }
};

// Trigger update
function performUpdate(component) {
  websocket.send(JSON.stringify({
    subject: "updater.perform_update",
    source: "frontend",
    body: {
      component: component,
      dry_run: false
    }
  }));
}
```

## Implementation Details

### Version Checking

- **Frequency:** Configurable (default: 24 hours)
- **Initial Delay:** 5 minutes after startup
- **Method:** GitHub API `/repos/{owner}/{repo}/releases/latest`
- **Comparison:** Semantic versioning using `packaging` library

### Update Process - Containerized Components

1. **Backup:** Current `docker-compose.yaml` saved to backups directory
2. **Update:** Image tag modified in compose file
3. **Pull:** `docker-compose pull <service>` downloads new image
4. **Restart:** `docker-compose up -d <service>` recreates container
5. **Verify:** Health checks confirm successful update

### Update Process - Python Application (Core)

1. **Download:** Fetch `.tar.gz` artifact from GitHub Releases
2. **Backup:** Archive current installation directory
3. **Stop:** Systemd service stopped (`systemctl stop dunebugger`)
4. **Extract:** New version extracted to installation directory
5. **Dependencies:** `pip3 install -r requirements.txt` updates packages
6. **Start:** Systemd service started (`systemctl start dunebugger`)
7. **Verify:** Health checks confirm successful update

### Rollback Mechanism

- **Automatic:** Triggered on post-update check failure
- **Backup Retention:** Timestamped backups in configured directory
- **Restore:** Most recent backup restored and service restarted

## Security Considerations

1. **No Remote Script Execution:** Updater doesn't execute arbitrary remote scripts
2. **Manifest Validation:** Update manifests are optional; updater has built-in procedures
3. **Version Verification:** Semantic versioning ensures valid updates only
4. **Backup Before Update:** All updates create backups before proceeding
5. **Health Checks:** Post-update validation ensures system remains operational

## What's Not Implemented (TODO)

The following features are planned but not yet implemented:

### 1. VERSION File Reading for Core
**File:** `dunebugger_updater.py`
**Method:** `_get_current_core_version()`

Currently returns "unknown". Needs implementation to:
- Read from `/opt/dunebugger/core/VERSION` file
- Or parse from Python package metadata
- Or execute `python -c "import version; print(version.__version__)"`

### 2. Advanced Manifest Actions
Some manifest actions are documented but not fully implemented:
- `checksum` verification for downloads
- `run_migrations` script execution
- `version_check` post-update validation

### 3. Update Manifest Generation
A helper tool or GitHub Action should be created to:
- Automatically generate update manifests during release
- Include checksums for artifacts
- Validate manifest structure

### 4. Progressive Rollout
Future enhancement to support:
- Staged rollouts (canary deployments)
- Rollback to specific versions (not just latest backup)
- Update scheduling (specific time windows)

### 5. Update Notifications
Enhancement for:
- Email notifications on available updates
- Slack/Discord webhooks for update events
- Frontend notifications via WebSocket

### 6. Multi-Device Updates
For fleet management:
- Coordinate updates across multiple devices
- Staggered update deployment
- Update status aggregation

## Testing

### Manual Testing

```bash
# Test update check
# Send WebSocket message: {"subject": "updater.check_updates", "source": "test", "body": {"force": true}}

# Test dry run
# Send WebSocket message: {"subject": "updater.perform_update", "source": "test", "body": {"component": "scheduler", "dry_run": true}}

# Test actual update (be careful!)
# Send WebSocket message: {"subject": "updater.perform_update", "source": "test", "body": {"component": "scheduler", "dry_run": false}}
```

### Automated Testing

Create test manifests and mock GitHub API responses to test:
- Version comparison logic
- Pre-update checks
- Update execution (with mocked system calls)
- Post-update checks
- Rollback procedures

## Troubleshooting

### Update Check Fails

**Symptom:** No update information available

**Possible Causes:**
- No internet connectivity
- GitHub API rate limit exceeded
- Repository or release not found
- Invalid configuration

**Solution:**
```bash
# Check logs
journalctl -u dunebugger-remote -f | grep -i update

# Test GitHub API access
curl https://api.github.com/repos/marco-svitol/dunebugger/releases/latest

# Check configuration
cat /opt/dunebugger/remote/config/dunebugger.conf
```

### Update Fails During Execution

**Symptom:** Update reports failure, service not updated

**Possible Causes:**
- Insufficient disk space
- Permission issues
- Network problems during download
- Service conflicts

**Solution:**
```bash
# Check disk space
df -h

# Check backup exists
ls -lh /opt/dunebugger/backups/

# Check service status
systemctl status dunebugger
docker ps

# Manual rollback if needed
cd /opt/dunebugger/backups
# Restore latest backup...
```

### Service Won't Start After Update

**Symptom:** Post-update checks fail, service not running

**Actions Taken:** Automatic rollback should trigger

**Manual Recovery:**
```bash
# Check logs
journalctl -u dunebugger -n 100

# Restore from backup
cd /opt/dunebugger/backups
# Find latest backup
ls -lt core.*.tar.gz | head -1
# Extract and restart...
```

## Best Practices

1. **Test Updates in Staging:** Always test updates on a non-production system first
2. **Monitor Logs:** Watch logs during and after updates
3. **Backup Externally:** Consider additional external backups
4. **Schedule Updates:** Perform updates during maintenance windows
5. **Verify Manifests:** Review update manifests before major updates
6. **Document Changes:** Keep release notes accessible
7. **Plan Rollbacks:** Understand rollback procedures before updating

## Architecture Decisions

### Why Update Manifests are Optional

The updater has built-in update procedures for both component types. Manifests provide additional control but aren't required. This approach:
- Works even if manifest is missing or malformed
- Provides sensible defaults for common update scenarios
- Allows gradual adoption of manifest-based updates
- Reduces dependency on external files

### Why Not Execute Remote Scripts

Executing arbitrary scripts from the internet poses security risks:
- **Malicious Code:** Compromised repository could execute harmful code
- **Validation:** Difficult to validate script safety programmatically
- **Auditability:** Hard to audit what scripts will do
- **Rollback:** Scripts might make irreversible changes

The manifest approach with declarative actions is safer and more predictable.

### Why Separate Manifests from Code

Update manifests are version-specific and should match the release:
- Different versions may have different update requirements
- Manifests are documentation of the update process
- Can be fetched independently of the artifact
- Easier to review and modify without code changes

## License

This module is part of the DuneBugger Remote component. See repository LICENSE file for details.
