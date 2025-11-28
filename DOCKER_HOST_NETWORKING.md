# Docker Host Networking Configuration

## Overview
This application is configured to run with Docker host networking mode to access the Raspberry Pi's actual network interfaces instead of the container's virtual interfaces.

## Changes Made

### 1. Docker Compose Configuration
- Added `network_mode: host` to the dunebugger-remote service
- Added volume mounts for `/proc` and `/sys` to access host system information
- The service now uses the host's network stack directly

### 2. System Info Improvements
- Added Docker detection in `dunebugger_system_info.py`
- Modified service state checking to handle Docker environment
- Services running in Docker containers return appropriate status

### 3. Network Info Improvements
- Added Docker interface filtering in `network_info.py`
- Filters out Docker-specific interfaces (docker*, br-*, veth*)
- Focuses on physical network interfaces (ethernet, WiFi, etc.)

### 4. Container Tools
- Added network utilities to Dockerfile: `iproute2`, `wireless-tools`, `net-tools`, `iputils-ping`, `procps`
- These tools enable proper network interface detection and WiFi information gathering

## Usage
When deploying on Raspberry Pi:

1. The container will use host networking
2. Network interfaces shown will be the Pi's actual interfaces (eth0, wlan0, etc.)
3. System service checks will correctly identify the Docker environment
4. WiFi information (SSID, signal strength) will be available for the Pi's wireless interface

## Security Considerations
- Host networking gives the container access to all host network interfaces
- This is necessary for monitoring the actual Pi network interfaces
- The container still runs as a non-root user for security