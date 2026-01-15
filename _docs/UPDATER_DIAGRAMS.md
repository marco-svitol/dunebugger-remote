# Component Updater - Visual Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DuneBugger Ecosystem                             │
│                                                                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │  Dunebugger     │  │  Scheduler      │  │  Remote         │         │
│  │  Core           │  │  (Container)    │  │  (Container)    │         │
│  │  (Python App)   │  │                 │  │                 │         │
│  │                 │  │  ┌───────────┐  │  │  ┌───────────┐  │         │
│  │  ┌───────────┐  │  │  │ Scheduler │  │  │  │  Remote   │  │         │
│  │  │   Main    │  │  │  │   App     │  │  │  │   App     │  │         │
│  │  │  Process  │  │  │  └───────────┘  │  │  │           │  │         │
│  │  └───────────┘  │  │                 │  │  │ ┌───────┐ │  │         │
│  │                 │  │  Image:         │  │  │ │Updater│ │  │         │
│  │  Service:       │  │  ghcr.io/...    │  │  │ │Module │ │  │         │
│  │  dunebugger     │  │  scheduler:1.0  │  │  │ └───────┘ │  │         │
│  │                 │  │                 │  │  │           │  │         │
│  │  Location:      │  │  In:            │  │  │  Image:   │  │         │
│  │  /opt/dunebugger│  │  docker-compose │  │  │  ghcr.io/ │  │         │
│  │  /core/         │  │  .yml           │  │  │  remote:1.0│ │         │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘         │
│         │                      │                      │                  │
│         └──────────────────────┴──────────────────────┘                  │
│                                │                                         │
│                    Managed by Updater Module                             │
└───────────────────────────────────────────────────────────────────────────┘
                                 │
                                 │ Checks for updates
                                 │ Downloads new versions
                                 │
                                 ▼
                 ┌─────────────────────────────────┐
                 │    GitHub Repositories          │
                 │                                 │
                 │  marco-svitol/dunebugger        │
                 │  • Releases (tar.gz)            │
                 │  • Tags: v1.0, v1.1, v1.2       │
                 │                                 │
                 │  marco-svitol/dunebugger-...    │
                 │  • Container Registry (GHCR)    │
                 │  • Tags: 1.0, 1.1, 1.2          │
                 │                                 │
                 │  marco-svitol/dunebugger-...    │
                 │  • Container Registry (GHCR)    │
                 │  • Tags: 1.0, 1.1, 1.2          │
                 └─────────────────────────────────┘
```

## Update Flow - High Level

```
┌──────────────┐
│   Trigger    │
│   Update     │
│   Check      │
└──────┬───────┘
       │
       ├─── Scheduled (every 24h)
       ├─── Manual (WebSocket)
       └─── On Demand (API call)
       │
       ▼
┌──────────────────────────────────────┐
│  Check GitHub for Latest Versions   │
│  • Query /releases/latest API        │
│  • Parse version tags                │
│  • Compare with current versions     │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  Update Available?                   │
└──────┬───────────────────────────────┘
       │
       ├─── NO ──► Report "Up to date"
       │
       YES
       │
       ▼
┌──────────────────────────────────────┐
│  User Initiates Update               │
│  (via WebSocket message)             │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  Execute Update Procedure            │
│  (see detailed flow below)           │
└──────┬───────────────────────────────┘
       │
       ├─── Success ──► Update complete
       │
       └─── Failure ──► Automatic rollback
```

## Detailed Update Procedure - Containerized Component

```
START: Update Scheduler v1.0 → v1.1
│
├─ Step 1: Pre-Update Checks
│  │
│  ├─ Check disk space (>500MB)        ✓
│  ├─ Verify network connectivity      ✓
│  └─ Check permissions                ✓
│
├─ Step 2: Backup
│  │
│  └─ Copy docker-compose.yml
│     to /opt/dunebugger/backups/
│     docker-compose.20260113_103000.yml
│
├─ Step 3: Modify Compose File
│  │
│  └─ Change:
│     image: ghcr.io/.../scheduler:1.0
│     to:
│     image: ghcr.io/.../scheduler:1.1
│
├─ Step 4: Pull New Image
│  │
│  └─ Execute:
│     docker-compose -f docker-compose.yml 
│     pull scheduler
│     
│     Output: Downloading new layers...
│             Pull complete!
│
├─ Step 5: Restart Container
│  │
│  └─ Execute:
│     docker-compose -f docker-compose.yml 
│     up -d scheduler
│     
│     Output: Recreating scheduler...
│             scheduler started
│
├─ Step 6: Post-Update Checks
│  │
│  ├─ Wait 5 seconds
│  ├─ Check container running           ✓
│  │  docker ps | grep scheduler
│  │  
│  └─ Check health endpoint             ✓
│     curl http://localhost:8080/health
│     Response: 200 OK
│
└─ Step 7: Complete
   │
   └─ Update version in memory
      Mark as current: v1.1
      Report success to user

END: Update successful
```

## Detailed Update Procedure - Python Application (Core)

```
START: Update Core v1.0 → v1.2
│
├─ Step 1: Pre-Update Checks
│  │
│  ├─ Check disk space (>1GB)          ✓
│  ├─ Check service is running         ✓
│  │  systemctl is-active dunebugger
│  └─ Verify permissions               ✓
│
├─ Step 2: Download Artifact
│  │
│  └─ Download from GitHub Releases:
│     https://github.com/.../dunebugger/
│     releases/download/v1.2.0/
│     dunebugger-1.2.0.tar.gz
│     
│     Save to: /tmp/dunebugger_update/
│
├─ Step 3: Backup Current Installation
│  │
│  └─ Create archive:
│     tar -czf 
│     /opt/dunebugger/backups/
│     core.20260113_103000.tar.gz
│     /opt/dunebugger/core/
│
├─ Step 4: Stop Service
│  │
│  └─ Execute:
│     systemctl stop dunebugger
│     
│     Wait for clean shutdown...
│
├─ Step 5: Extract New Version
│  │
│  ├─ Remove old installation:
│  │  rm -rf /opt/dunebugger/core/*
│  │
│  └─ Extract new:
│     tar -xzf dunebugger-1.2.0.tar.gz
│     -C /opt/dunebugger/core/
│
├─ Step 6: Install Dependencies
│  │
│  └─ Execute:
│     pip3 install -r 
│     /opt/dunebugger/core/requirements.txt
│     
│     Installing packages...
│     All packages installed successfully
│
├─ Step 7: Start Service
│  │
│  └─ Execute:
│     systemctl start dunebugger
│     
│     Service starting...
│
├─ Step 8: Post-Update Checks
│  │
│  ├─ Wait 10 seconds for startup
│  │
│  ├─ Check service active              ✓
│  │  systemctl is-active dunebugger
│  │  Result: active
│  │
│  └─ Check health endpoint             ✓
│     curl http://localhost:5000/health
│     Response: 200 OK
│     {"status": "healthy", "version": "1.2.0"}
│
└─ Step 9: Complete
   │
   ├─ Update version in memory
   │  Mark as current: v1.2.0
   │
   └─ Cleanup temporary files
      rm -rf /tmp/dunebugger_update/
      
END: Update successful
```

## Rollback Procedure

```
Rollback Triggered (Post-check failed)
│
├─ Container Rollback:
│  │
│  ├─ Restore docker-compose.yml
│  │  from latest backup
│  │
│  ├─ Execute:
│  │  docker-compose up -d scheduler
│  │
│  └─ Verify service running
│
└─ Python App Rollback:
   │
   ├─ Stop service:
   │  systemctl stop dunebugger
   │
   ├─ Remove failed installation:
   │  rm -rf /opt/dunebugger/core/*
   │
   ├─ Restore from backup:
   │  tar -xzf /opt/dunebugger/backups/
   │  core.20260113_103000.tar.gz
   │  -C /opt/dunebugger/
   │
   ├─ Start service:
   │  systemctl start dunebugger
   │
   └─ Report rollback to user

END: Rolled back to previous version
```

## Component Interaction During Update

```
┌─────────────────────────────────────────────────────────────┐
│                     Update Interaction                       │
└─────────────────────────────────────────────────────────────┘

Frontend (Browser)
    │
    │ 1. Send update request
    │    {"subject": "updater.perform_update",
    │     "body": {"component": "scheduler"}}
    │
    ▼
WebSocket Connection
    │
    │ 2. Forward to handler
    │
    ▼
WebSocket Message Handler
    │
    │ 3. Call updater
    │    await component_updater.update_component("scheduler")
    │
    ▼
Component Updater
    │
    │ 4a. Containerized update
    │     ├─ Modify docker-compose.yml
    │     ├─ docker-compose pull
    │     └─ docker-compose up -d
    │
    │ 4b. Python app update
    │     ├─ Download from GitHub
    │     ├─ Stop systemd service
    │     ├─ Extract files
    │     └─ Start systemd service
    │
    ▼
System/Docker
    │
    │ 5. Execute update
    │
    ▼
Component Updater
    │
    │ 6. Run health checks
    │
    ▼
WebSocket Message Handler
    │
    │ 7. Send result
    │    {"subject": "update_result",
    │     "body": {"success": true}}
    │
    ▼
Frontend (Browser)
    │
    │ 8. Display success
    │
    ▼
[Update Complete]
```

## File System Layout After Updates

```
/opt/dunebugger/
│
├── docker-compose.yml          ← Updated with new image tags
│
├── core/                       ← Python application installation
│   ├── app/
│   ├── requirements.txt
│   ├── VERSION                 ← Version identifier
│   └── ...
│
├── remote/                     ← Remote component (this component)
│   ├── app/
│   │   ├── dunebugger_updater.py  ← Updater module
│   │   └── ...
│   └── config/
│       └── dunebugger.conf     ← Updater configuration
│
├── backups/                    ← Automatic backups
│   ├── core.20260113_103000.tar.gz
│   ├── core.20260113_110000.tar.gz
│   ├── docker-compose.20260113_103000.yml
│   └── docker-compose.20260113_110000.yml
│
└── logs/                       ← Update logs
    └── updates.log
```

## Configuration Flow

```
dunebugger.conf
    │
    │ [Updater]
    │ updateCheckIntervalHours = 24
    │ dockerComposePath = /opt/dunebugger/docker-compose.yml
    │ coreInstallPath = /opt/dunebugger/core
    │ backupPath = /opt/dunebugger/backups
    │
    ▼
dunebugger_settings.py
    │
    │ Validates and loads configuration
    │
    ▼
ComponentUpdater.__init__(config)
    │
    │ Initializes with config values
    │ Sets up paths and intervals
    │
    ▼
Periodic Check Loop
    │
    │ Every 24 hours (or configured interval)
    │ Check GitHub for new versions
    │ Update component version info
    │
    ▼
System Info Model
    │
    │ Exposes version info to
    │ frontend via WebSocket
```

## Version Comparison Logic

```
GitHub Release Tag        Local Version          Result
─────────────────────────────────────────────────────────
v1.2.0                    1.1.0                  Update Available
v1.1.5                    1.1.5                  Up to Date
v2.0.0                    1.9.9                  Update Available
v1.0.0-beta               1.0.0                  No Update
v1.1.0                    1.2.0                  No Update (local newer)

Semantic Versioning Comparison:
    MAJOR.MINOR.PATCH
    
    Update if: GitHub version > Local version
    Using: packaging.version.parse()
```
