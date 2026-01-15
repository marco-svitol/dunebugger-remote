# Dunebugger-remote
The dunebugger component that handles remote communication with the dunbugger server

## Features

- Remote WebSocket communication with dunebugger cloud services
- NATS message queue integration for local component communication
- System information collection and reporting
- NTP availability monitoring
- Internet connection monitoring
- **Component version management and automated updates** (see [UPDATER_MODULE.md](UPDATER_MODULE.md))

## Component Updater

The remote component includes a sophisticated updater module that manages version tracking and automated updates for all DuneBugger components:

- **Automatic version checking** (configurable interval, default 24 hours)
- **Manual update triggering** via WebSocket
- **Supports both containerized and non-containerized components**
- **Safe update procedures** with pre-checks, health validation, and automatic rollback
- **Backup and restore** functionality

For complete documentation, see [UPDATER_MODULE.md](UPDATER_MODULE.md)

### Quick Start - Using the Updater

```javascript
// Check for updates via WebSocket
websocket.send(JSON.stringify({
  subject: "updater.check_updates",
  source: "frontend",
  body: { force: true }
}));

// Perform an update
websocket.send(JSON.stringify({
  subject: "updater.perform_update",
  source: "frontend",
  body: {
    component: "scheduler",
    dry_run: false
  }
}));
```

## Using NATS
docker run -d --name nats-server -p 4222:4222 -p 8222:8222 nats -m 8222
