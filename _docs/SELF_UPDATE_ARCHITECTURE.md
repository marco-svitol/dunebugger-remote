# Update Architecture - Hybrid Coordinator Pattern

## Overview

This document describes the hybrid update architecture for DuneBugger components. The architecture solves the container self-update problem without requiring Docker-in-Docker or elevated container privileges.

## Problem Statement

Containers cannot easily update themselves because:
- No access to host Docker daemon from inside container
- Installing Docker in container increases image size (~100MB+)
- Running privileged containers is a security risk
- Subprocess calls from container can't execute host commands (docker, docker-compose, systemctl)

## Solution: Hybrid Coordinator Pattern

### Architecture Components

1. **dunebugger-remote** (Coordinator, runs in container):
   - Checks for updates from GitHub API
   - Provides WebSocket API for user interaction
   - Tracks component versions and health status
   - **Does not execute Docker/system commands**
   - Writes update requests to shared volume
   - Polls for status responses

2. **update-coordinator** (Executor, runs on host):
   - Systemd service running on Raspberry Pi host
   - Watches `/var/dunebugger/updates/requests/` directory (inotify)
   - Executes component-specific update scripts
   - Has full access to Docker daemon and system commands
   - Writes status to `/var/dunebugger/updates/status/`
   - Logs to `/var/log/dunebugger/update-coordinator.log`

3. **Component Scripts** (on host):
   - Each component provides `update.sh`, `rollback.sh`, `health-check.sh`
   - Located in component directories (e.g., `/opt/dunebugger/remote/`)
   - Executed by coordinator with proper privileges
   - Standard interface across all components

### Communication Protocol

**Request Format** (`/var/dunebugger/updates/requests/<UUID>.json`):
```json
{
  "component": "remote|scheduler|core",
  "action": "update|rollback|health",
  "version": "1.2.3",
  "request_id": "uuid-1234-5678",
  "timestamp": "2026-01-16T10:30:00Z"
}
```

**Response Format** (`/var/dunebugger/updates/status/<UUID>.json`):
```json
{
  "request_id": "uuid-1234-5678",
  "component": "remote",
  "action": "update",
  "success": true,
  "message": "Update completed successfully",
  "output": "stdout from script...",
  "error": "stderr from script...",
  "timestamp": "2026-01-16T10:31:00Z"
}
```

## Communication Flow

```
┌────────────────────────────────────────────────────────────────────┐
│ 1. User triggers update via WebSocket                              │
│    {"subject": "updater.perform_update", "body": {"component": ... │
└────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│ 2. dunebugger-remote (container)                                   │
│    ComponentUpdater.update_component():                            │
│    - Checks version from GitHub                                    │
│    - Creates update request JSON with UUID                         │
│    - Writes to /var/dunebugger/updates/requests/UUID.json         │
│    - Begins polling for status                                     │
└────────────────────────────────────────────────────────────────────┘
                                │
                                ▼ (inotify file event)
┌────────────────────────────────────────────────────────────────────┐
│ 3. update-coordinator (host systemd service)                       │
│    UpdateRequestHandler.process_request():                         │
│    - Detects new request file (watchdog observer)                  │
│    - Validates request format and component                        │
│    - Verifies script exists                                        │
│    - Executes: /opt/dunebugger/COMPONENT/update.sh VERSION        │
└────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│ 4. Component update script (bash)                                  │
│    For containers:                                                 │
│    - Backup docker-compose.yml                                     │
│    - Update image tag with sed                                     │
│    - docker-compose pull COMPONENT                                 │
│    - docker-compose up -d --no-deps COMPONENT                      │
│                                                                     │
│    For Python apps:                                                │
│    - Download release artifact from GitHub                         │
│    - Backup current installation                                   │
│    - systemctl stop SERVICE                                        │
│    - Extract new version                                           │
│    - pip3 install -r requirements.txt                              │
│    - systemctl start SERVICE                                       │
│                                                                     │
│    Returns: exit code (0=success, non-zero=failure)                │
└────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│ 5. update-coordinator                                              │
│    - Captures script stdout/stderr                                 │
│    - Captures exit code                                            │
│    - Creates status JSON with result                               │
│    - Writes to /var/dunebugger/updates/status/UUID.json           │
│    - Deletes request file                                          │
└────────────────────────────────────────────────────────────────────┘
                                │
                                ▼ (polling every 1 second)
┌────────────────────────────────────────────────────────────────────┐
│ 6. dunebugger-remote (container)                                   │
│    ComponentUpdater._wait_for_status():                            │
│    - Polls for status file (10 minute timeout)                     │
│    - Reads result                                                  │
│    - Sends response to user via WebSocket                          │
│    - Deletes status file                                           │
│    - Updates component version info                                │
└────────────────────────────────────────────────────────────────────┘
```

## Key Benefits

### 1. Security
- Container runs unprivileged (no root, no Docker socket)
- Clear security boundary between container and host
- Coordinator validates all requests before execution

### 2. Simplicity
- Container image stays minimal (~80MB saved)
- No Docker-in-Docker complexity
- Standard bash scripts for updates (easy to debug)
- File-based communication (no network complexity)

### 3. Flexibility
- Each component controls its own update logic
- Scripts can be tested independently
- Easy to add new components
- Update procedures can evolve per component

### 4. Reliability
- Coordinator runs as systemd service (auto-restart)
- Comprehensive logging at both layers
- Atomic file operations
- Rollback capability in scripts

### 5. Maintainability
- Clear separation of concerns
- Coordinator is ~300 lines of Python
- Component scripts are simple bash
- Easy to understand and modify

## Component Update Scripts

Each component must provide three scripts with standard interface:

### update.sh
```bash
#!/bin/bash
# Usage: ./update.sh VERSION
# Exit: 0 = success, non-zero = failure

VERSION="$1"

# 1. Backup current state
# 2. Perform update (pull image, extract files, etc.)
# 3. Restart service/container
# 4. Verify health
# 5. Rollback on failure

exit 0  # or 1 on failure
```

### rollback.sh
```bash
#!/bin/bash
# Usage: ./rollback.sh
# Exit: 0 = success, non-zero = failure

# 1. Find latest backup
# 2. Stop current service/container
# 3. Restore from backup
# 4. Start service/container
# 5. Verify health

exit 0  # or 1 on failure
```

### health-check.sh
```bash
#!/bin/bash
# Usage: ./health-check.sh
# Exit: 0 = healthy, non-zero = unhealthy

# For containers: docker ps --filter name=... --filter status=running
# For services: systemctl is-active SERVICE

exit 0  # or 1 if unhealthy
```

See `_host_coordinator/component-scripts/` for complete examples.

## Deployment

### 1. Install Coordinator on Host

```bash
cd _host_coordinator
sudo ./install.sh
```

This installs:
- Python script at `/opt/dunebugger/update-coordinator/update-coordinator.py`
- Systemd service `dunebugger-update-coordinator`
- Directories at `/var/dunebugger/updates/{requests,status}/`
- Installs Python watchdog library

### 2. Install Component Scripts

```bash
# Copy scripts to component directories
sudo mkdir -p /opt/dunebugger/{core,scheduler,remote}
sudo cp _host_coordinator/component-scripts/core/*.sh /opt/dunebugger/core/
sudo cp _host_coordinator/component-scripts/scheduler/*.sh /opt/dunebugger/scheduler/
sudo cp _host_coordinator/component-scripts/remote/*.sh /opt/dunebugger/remote/

# Make executable
sudo chmod +x /opt/dunebugger/*/update.sh
sudo chmod +x /opt/dunebugger/*/rollback.sh
sudo chmod +x /opt/dunebugger/*/health-check.sh
```

### 3. Configure Docker Compose

Mount shared volume:

```yaml
services:
  remote:
    image: ghcr.io/marco-svitol/dunebugger-remote:latest
    volumes:
      - /var/dunebugger/updates:/var/dunebugger/updates  # Required!
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
```

### 4. Verify

```bash
# Check coordinator is running
sudo systemctl status dunebugger-update-coordinator

# View logs
sudo journalctl -u dunebugger-update-coordinator -f

# Test update (manual)
cat > /var/dunebugger/updates/requests/test-123.json << EOF
{
  "component": "remote",
  "action": "health",
  "request_id": "test-123",
  "timestamp": "$(date -Iseconds)"
}
EOF

# Check status
cat /var/dunebugger/updates/status/test-123.json
```

## Error Handling

### Coordinator Errors

- **Script not found**: Returns error status immediately
- **Script timeout**: Kills script after 10 minutes, returns timeout status
- **Invalid request**: Returns validation error status
- **Script fails**: Captures exit code and stderr, returns failure status

### Script Errors

- **Update fails**: Script should rollback automatically and exit non-zero
- **Health check fails**: Script exits non-zero
- **Rollback needed**: Coordinator or user can trigger rollback action

### Container Errors

- **Status file not created**: Container timeout (10 minutes)
- **Coordinator not running**: Update request never processed
- **Shared volume not mounted**: Request write fails, clear error to user

## Troubleshooting

### Updates not working

```bash
# 1. Check coordinator is running
sudo systemctl status dunebugger-update-coordinator

# 2. Check shared volume exists
ls -la /var/dunebugger/updates/

# 3. Check shared volume is mounted in container
docker exec dunebugger-remote ls -la /var/dunebugger/updates/

# 4. Check component scripts exist
ls -la /opt/dunebugger/remote/*.sh

# 5. View coordinator logs
sudo journalctl -u dunebugger-update-coordinator -n 100

# 6. Test script manually
sudo /opt/dunebugger/remote/health-check.sh
echo "Exit code: $?"
```

### Script debugging

```bash
# Run script manually with verbose output
sudo bash -x /opt/dunebugger/remote/update.sh 1.2.3

# Check script permissions
ls -la /opt/dunebugger/remote/update.sh

# Verify docker-compose.yml exists
ls -la /opt/dunebugger/docker-compose.yml
```

## Security Considerations

### Container Security
- Runs as non-root user (`appuser`)
- No privileged mode required
- No Docker socket mount required
- Limited to writing request files

### Coordinator Security
- Runs as root (required for Docker commands)
- Validates all requests before execution
- Only executes pre-defined scripts in known locations
- Resource limits via systemd (20% CPU, 256MB RAM)
- Protected system directories (`ProtectSystem=full`)

### Shared Volume Security
- Currently world-readable/writable (0755)
- Consider restricting permissions in production
- Could implement request signing/validation
- Could use separate UID/GID for coordination

## Future Enhancements

### Potential Improvements

1. **Request Signing**: Cryptographically sign requests to prevent unauthorized updates
2. **Rate Limiting**: Prevent update spam
3. **Update Scheduling**: Schedule updates for specific times
4. **Multi-Component Updates**: Update multiple components atomically
5. **Progress Streaming**: Stream update progress instead of polling
6. **Coordinator Self-Update**: Allow coordinator to update itself safely
7. **Web UI**: Admin interface for update management

### Not Planned

- Update manifest files (replaced by simple scripts)
- Pre-check validation (handled by scripts)
- Complex rollback logic (scripts handle it)

## References

- [_host_coordinator/README.md](../_host_coordinator/README.md) - Coordinator setup
- [_host_coordinator/component-scripts/README.md](../_host_coordinator/component-scripts/README.md) - Script examples
- [UPDATER_MODULE.md](../UPDATER_MODULE.md) - User documentation
- [_docs/docker-compose-example.yml](_docs/docker-compose-example.yml) - Deployment example
