#!/usr/bin/env python3
"""
Component Updater for DuneBugger Remote
Manages version checking and updates for all dunebugger components
"""

import asyncio
import aiohttp
import yaml
import json
import time
import uuid
from pathlib import Path
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from packaging import version as pkg_version
from dunebugger_logging import logger
from dunebugger_settings import settings
from utils import parse_semver

@dataclass
class ComponentHealth:
    """Holds health status for a component"""
    name: str
    running: bool = False
    latest_heartbeat: Optional[datetime] = None
    heartbeat_ttl: int = 45  # seconds

@dataclass
class ComponentVersion:
    """Holds version information for a component"""
    name: str
    current_version: str
    version_fetcher: Callable[[], str] = field(default=None, repr=False, compare=False)
    latest_version: Optional[str] = None
    update_available: bool = False
    last_checked: Optional[datetime] = None
    release_url: Optional[str] = None
    release_notes: Optional[str] = None
    component_type: str = "unknown"  # 'python_app', 'container'
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        # Exclude version_fetcher from serialization
        data.pop('version_fetcher', None)
        if self.last_checked:
            data['last_checked'] = self.last_checked.isoformat()
        return data


class ComponentUpdater:
    """Manages version checking and updates for all dunebugger components"""
    
    REPOS = {
        "core": "dunebugger",
        "scheduler": "dunebugger-scheduler",
        "remote": "dunebugger-remote"
    }
    
    def __init__(self):
        self.components: Dict[str, Dict[str, any]] = {}
        self.github_account = getattr(settings, 'githubAccount')
        self.include_prerelease = getattr(settings, 'includePrerelease', False)
        self.check_interval_hours = getattr(settings, 'updateCheckIntervalHours', 24)
        self.core_install_path = Path(getattr(settings, 'coreInstallPath', '/opt/dunebugger/core'))
        self.backup_path = Path(getattr(settings, 'backupPath', '/opt/dunebugger/backups'))
        self.docker_compose_path = Path(getattr(settings, 'dockerComposePath', '/docker-compose.yml'))
        
        # Shared volume paths for coordinator communication
        self.update_request_dir = Path("/var/dunebugger/updates/requests")
        self.update_status_dir = Path("/var/dunebugger/updates/status")
        
        # Periodic check task
        self._periodic_check_task = None
        self._running = False
        
        self._init_components()
        
    def _init_components(self):
        """Initialize component version tracking"""
        # Initialize parent dictionary keys first
        self.components['core'] = {}
        self.components['scheduler'] = {}
        self.components['remote'] = {}
        
        self.components['core']['version_info'] = ComponentVersion(
            name='dunebugger-core',
            current_version=self._get_python_app_version(self.core_install_path),
            version_fetcher=lambda: self._get_python_app_version(self.core_install_path),
            component_type='python_app'
        )
        self.components['scheduler']['version_info'] = ComponentVersion(
            name='dunebugger-scheduler',
            current_version=self._get_container_version('scheduler'),
            version_fetcher=lambda: self._get_container_version('scheduler'),
            component_type='container'
        )
        self.components['remote']['version_info'] = ComponentVersion(
            name='dunebugger-remote',
            current_version=self._get_current_remote_version(),
            version_fetcher=lambda: self._get_current_remote_version(),
            component_type='container'
        )

        self.components['core']['health'] = ComponentHealth(name='dunebugger-core')
        self.components['scheduler']['health'] = ComponentHealth(name='dunebugger-scheduler')
        self.components['remote']['health'] = ComponentHealth(name='dunebugger-remote', running=True, latest_heartbeat=time.time(), heartbeat_ttl=315576000)

        
        logger.info(f"Initialized component versions - Core: {self.components['core']['version_info'].current_version}, "
                   f"Scheduler: {self.components['scheduler']['version_info'].current_version}, "
                   f"Remote: {self.components['remote']['version_info'].current_version}")
    
    async def start_periodic_check(self):
        """Start the periodic update checking task"""
        if self._periodic_check_task is None:
            self._running = True
            self._periodic_check_task = asyncio.create_task(self._periodic_check_loop())
            logger.info(f"Started periodic update checking (interval: {self.check_interval_hours}h)")
    
    async def stop_periodic_check(self):
        """Stop the periodic update checking task"""
        self._running = False
        if self._periodic_check_task:
            self._periodic_check_task.cancel()
            try:
                await self._periodic_check_task
            except asyncio.CancelledError:
                pass
            self._periodic_check_task = None
            logger.info("Stopped periodic update checking")
    
    async def _periodic_check_loop(self):
        """Periodically check for updates"""
        # Initial delay of 5 minutes after startup
        # TODO: make this configurable?
        #await asyncio.sleep(300)
        
        while self._running:
            try:
                logger.info("Running scheduled update check")
                await self.check_updates(force=False)
                
                # Sleep for the configured interval
                await asyncio.sleep(self.check_interval_hours * 3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic update check: {e}")
                # Wait 1 hour before retrying on error
                await asyncio.sleep(3600)
    
    async def check_updates(self, force: bool = False) -> Dict[str, ComponentVersion]:
        """
        Check for available updates for all components
        
        Args:
            force: Force check even if last check was recent
            
        Returns:
            Dictionary of components with update information
        """
        results = {}
        
        for component_key, component in self.components.items():
            version_info = component['version_info']
            
            # Refresh current version from source before checking for updates
            self._refresh_component_version(component_key)
            
            # Check if we need to check (based on interval)
            if not force and version_info.last_checked:
                time_since_check = datetime.now() - version_info.last_checked
                if time_since_check < timedelta(hours=self.check_interval_hours):
                    logger.debug(f"Skipping {component_key} check (last checked {time_since_check.seconds//3600}h ago)")
                    results[component_key] = version_info
                    continue
            
            try:
                latest = await self._fetch_latest_version(self.REPOS[component_key])
                version_info.latest_version = latest['version']
                version_info.prerelease = latest.get('prerelease', False)
                version_info.release_url = latest['url']
                version_info.release_notes = latest['notes']
                version_info.update_available = self._compare_versions(
                    version_info.current_version, 
                    version_info.latest_version
                )
                version_info.last_checked = datetime.now()
                
                logger.info(f"{component_key}: current={version_info.current_version}, "
                           f"latest={version_info.latest_version}, "
                           f"update_available={version_info.update_available}")
                
            except Exception as e:
                logger.error(f"Failed to check updates for {component_key}: {e}")
            
            results[component_key] = version_info
        
        return results
    
    async def _fetch_latest_version(self, repo_name: str) -> dict:
        """
        Fetch latest release from GitHub API, filtering by prerelease setting.
        
        Parses the tag_name to extract version information.
        """
        url = f"https://api.github.com/repos/{self.github_account}/{repo_name}/releases"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    releases = await response.json()
                    
                    if not releases:
                        raise Exception(f"No releases found for {repo_name}")
                    
                    # Filter releases based on prerelease setting
                    # If include_prerelease is True, include all releases (prerelease and non-prerelease)
                    # If include_prerelease is False, only include non-prerelease releases
                    filtered_releases = [
                        r for r in releases 
                        if not r.get('draft', False) and (self.include_prerelease or not r.get('prerelease', False))
                    ]
                    
                    if not filtered_releases:
                        prerelease_type = "prerelease or non-prerelease" if self.include_prerelease else "non-prerelease"
                        raise Exception(f"No {prerelease_type} releases found for {repo_name}")
                    
                    # The releases are ordered by created_at descending, so first is latest
                    latest = filtered_releases[0]
                    
                    # Parse tag_name to get version
                    tag_version = latest['tag_name'].lstrip('v')
                    return {
                        'version': tag_version,
                        'version_info': self._parse_tag_to_version_info(tag_version, latest.get('prerelease', False)),
                        'prerelease': latest.get('prerelease', False),
                        'url': latest['html_url'],
                        'notes': latest.get('body', ''),
                        'assets': latest.get('assets', [])
                    }
                else:
                    raise Exception(f"GitHub API returned {response.status}")
    
    def _parse_tag_to_version_info(self, tag_version: str, is_prerelease: bool) -> dict:
        """
        Parse tag name into version info dict.
        
        Args:
            tag_version: Version string from tag (e.g., "1.0.0-beta.3")
            is_prerelease: Whether the release is marked as prerelease
            
        Returns:
            dict with version info
        """
        # Parse version string
        if '-' in tag_version:
            parts = tag_version.split('-', 1)
            version = parts[0]
            prerelease = parts[1]
        else:
            version = tag_version
            prerelease = None
        
        return {
            'version': version,
            'prerelease': prerelease,
            'build_type': 'prerelease' if is_prerelease else 'release',
            'build_number': 0,  # Unknown from tag alone
            'commit': 'unknown',
            'full_version': tag_version
        }
    
    async def update_components(self) -> Dict[str, dict]:
        """
        Update all components that have updates available
        
        Returns:
            Dictionary with component keys and update results
        """
        results = {}
        
        for component_key, component in self.components.items():
            version_info = component['version_info']
            if version_info.update_available:
                logger.info(f"Updating component: {component_key}")
                result = await self._update_component(component_key)
                results[component_key] = result
            else:
                logger.info(f"No update available for component: {component_key}")
                results[component_key] = {"success": False, "message": "No update available"}
        
        return results
    
    def _verify_update_order_requirement(self, component_key: str) -> dict:
        """
        Verify that if there are updates available for multiple components,
        'remote' must always be updated first.
        
        Args:
            component_key: The component being updated
            
        Returns:
            Dictionary with success status, message, and level
        """
        # If updating remote itself, no check needed
        if component_key == 'remote':
            return {"success": True, "message": ""}
        
        # Check if remote has an available update
        remote_version_info = self.components.get('remote', {}).get('version_info')
        if remote_version_info and remote_version_info.update_available:
            msg = f"Cannot update {component_key} before remote. Remote has an available update and must be updated first."
            logger.warning(msg)
            return {
                "success": False, 
                "message": msg,
                "level": "error"
            }
        
        return {"success": True, "message": ""}

    async def update_component(self, component_key, dry_run: bool = False) -> dict:
        """
        Update a specific component via host coordinator
        
        Writes update request to shared volume and polls for status response.
        The host coordinator executes the actual update script.
        
        Args:
            component_key: 'core', 'scheduler', or 'remote'
            dry_run: If True, only simulate the update (not supported yet)
            
        Returns:
            Dictionary with success status and message
        """
        component = self.components.get(component_key)

        # If the component is not found, return error
        if not component:
            return {"success": False, "message": f"Unknown component: {component_key}", "level": "error"}

        # Verify update order requirement: remote must be updated first if it has updates available
        order_check = self._verify_update_order_requirement(component_key)
        if not order_check["success"]:
            return order_check

        version_info = component['version_info']
        if not version_info.update_available:
            return {"success": False, "message": f"No update available for {component_key}", "level": "info"}
        
        logger.info(f"Requesting update for {component_key} from {version_info.current_version} to {version_info.latest_version}")
        
        try:
            # Write update request to shared volume
            request_id = str(uuid.uuid4())
            request = {
                "component": component_key,
                "action": "update",
                "version": version_info.latest_version,
                "request_id": request_id,
                "timestamp": datetime.now().isoformat()
            }
            
            # Ensure request directory exists
            self.update_request_dir.mkdir(parents=True, exist_ok=True)
            
            request_file = self.update_request_dir / f"{request_id}.json"
            with open(request_file, 'w') as f:
                json.dump(request, f, indent=2)
            
            logger.info(f"Update request written: {request_file}")
            
            # Poll for status response
            status = await self._wait_for_status(request_id, timeout=600)  # 10 minute timeout
            
            if status:
                if status.get('success'):
                    logger.info(f"Successfully updated {component_key} to {version_info.latest_version}")
                    # Refresh version from source to confirm update
                    self._refresh_component_version(component_key)
                    version_info.update_available = False
                    return {
                        "success": True,
                        "message": status.get('message', f"Successfully updated {component_key}"),
                        "level": "info",
                        "output": status.get('output', '')
                    }
                else:
                    logger.error(f"Update failed for {component_key}: {status.get('error')}")
                    return {
                        "success": False,
                        "message": status.get('message', 'Update failed'),
                        "level": "error",
                        "error": status.get('error', '')
                    }
            else:
                logger.error(f"Update timeout for {component_key} - no status received")
                return {
                    "success": False,
                    "message": "Update timeout - coordinator did not respond",
                    "level": "error"
                }
            
        except Exception as e:
            logger.error(f"Update failed for {component_key}: {e}", exc_info=True)
            return {"success": False, "message": f"Update failed: {str(e)}", "level": "error"}
    
    def _compare_versions(self, current: str, latest: str) -> bool:
        """
        Compare version strings using semantic versioning rules.
        
        Returns True if latest > current (update available).
        
        This uses the parse_semver function which properly handles:
        - Release vs prerelease versions (1.0.0 > 1.0.0-beta.3)
        - Prerelease ordering (beta.2 < beta.3)
        - Development versions (handled by ignoring .dev suffixes in comparison)
        """
        try:
            # Parse both versions using semantic versioning
            current_parsed = parse_semver(current)
            latest_parsed = parse_semver(latest)
            
            # Compare the parsed tuples
            # Tuple format: (base_version_tuple, is_release, prerelease_tuple)
            # Python tuple comparison naturally handles our ordering
            return latest_parsed > current_parsed
            
        except Exception as e:
            logger.warning(f"Semantic version comparison failed: {e}, falling back to packaging library")
            # Fallback to packaging library
            try:
                return pkg_version.parse(latest) > pkg_version.parse(current)
            except Exception as e2:
                logger.warning(f"Packaging library comparison also failed: {e2}, using string comparison")
                return latest != current
    
    def _is_version_compatible(self, current: str, minimum: str) -> bool:
        """Check if current version meets minimum requirement"""
        try:
            return pkg_version.parse(current) >= pkg_version.parse(minimum)
        except Exception as e:
            logger.warning(f"Version compatibility check failed: {e}")
            return True  # Be permissive on error
    
    def set_component_version(self, component_key: str, version: str):
        """Manually set the current version of a component"""
        if component_key in self.components:
            self.components[component_key]['version_info'].current_version = version
            logger.info(f"Set {component_key} version to {version}")
        else:
            logger.warning(f"Attempted to set version for unknown component: {component_key}")

    def get_component_version(self, component_key: str) -> Optional[str]:
        """Get the current version of a component"""
        component = self.components.get(component_key)
        if component:
            return component['version_info'].current_version
        return None
    
    def set_component_running(self, component_key: str):
        """Set the running status of a component"""
        if component_key in self.components:

            """Set the heartbeat core flag to alive and update timestamp"""
            self.components[component_key]['health'].running = True
            self.components[component_key]['health'].latest_heartbeat = time.time()
        else:
            logger.warning(f"Attempted to set running status for unknown component: {component_key}")

    def get_component_running(self, component_key: str) -> Optional[bool]:
        """Get the running status of a component"""
        component_health = self.components.get(component_key)['health']
        if component_health:
            """Check if the heartbeat core flag is alive (within TTL)"""
            if not component_health.running:
                return False
            
            current_time = time.time()
            if current_time - component_health.latest_heartbeat > component_health.heartbeat_ttl:
                component_health.running = False
                logger.debug("Heartbeat core flag expired (TTL exceeded)")
                return False
            
            return True
        else:
            logger.warning(f"Attempted to get running status for unknown component: {component_key}")
        return None

    def _get_current_remote_version(self) -> str:
        """Get current remote (self) version"""
        try:
            from version import get_version_info
            return get_version_info()['full_version']
        except Exception as e:
            logger.error(f"Error getting remote version: {e}")
            return "unknown"
    
    def _get_python_app_version(self, install_path: Path) -> str:
        """
        Get version of a Python application from VERSION file.
        
        Supports both new JSON format and legacy single-line format.
        
        Args:
            install_path: Path to the Python application installation directory
            
        Returns:
            Full version string from VERSION file or 'unknown' if not found
        """
        try:
            version_file = install_path / 'VERSION'
            if version_file.exists():
                with open(version_file, 'r') as f:
                    content = f.read().strip()
                    
                    # Try to parse as JSON (new format)
                    try:
                        version_data = json.loads(content)
                        # Return full_version from JSON
                        return version_data.get('full_version', 'unknown')
                    except json.JSONDecodeError:
                        # Legacy format: single line with version string
                        # Format could be "1.0.0-beta.3" or "1.0.0-beta.3-build85"
                        return content
            else:
                logger.warning(f"VERSION file not found at {version_file}")
                return "unknown"
        except Exception as e:
            logger.error(f"Error reading version from {install_path}: {e}")
            return "unknown"
    
    def _get_container_version(self, service_name: str) -> str:
        """Get version of a containerized service from Docker image tag
        
        Reads the docker-compose.yml file (must be mounted into container).
        
        Args:
            service_name: Name of the service in docker-compose.yml
            
        Returns:
            Version string from Docker image tag or 'unknown' if not found
        """
        try:
            if not self.docker_compose_path.exists():
                logger.warning(f"Docker compose file not found at {self.docker_compose_path}")
                return "unknown"
            
            with open(self.docker_compose_path, 'r') as f:
                compose_config = yaml.safe_load(f)
            
            service = compose_config.get('services', {}).get(service_name)
            if service and 'image' in service:
                image = service['image']
                # Extract tag from image (format: name:tag)
                if ':' in image:
                    version = image.split(':')[-1]
                    return version
                else:
                    logger.warning(f"No tag found in {service_name} image: {image}")
                    return "latest"
            else:
                logger.warning(f"Service '{service_name}' not found in docker-compose.yml")
                return "unknown"
        except Exception as e:
            logger.error(f"Error getting version for service '{service_name}': {e}")
            return "unknown"
    
    def _refresh_component_version(self, component_key: str) -> bool:
        """Refresh the current version of a component from its source
        
        Args:
            component_key: Key of the component to refresh
            
        Returns:
            True if version was refreshed, False on error
        """
        try:
            component = self.components.get(component_key)
            if not component:
                logger.warning(f"Cannot refresh version for unknown component: {component_key}")
                return False
            
            version_info = component['version_info']
            
            if not version_info.version_fetcher:
                logger.warning(f"No version fetcher defined for component: {component_key}")
                return False
            
            old_version = version_info.current_version
            
            # Call the stored version fetcher function
            new_version = version_info.version_fetcher()
            
            version_info.current_version = new_version
            
            if old_version != new_version:
                logger.info(f"Refreshed {component_key} version: {old_version} -> {new_version}")
            else:
                logger.debug(f"Version unchanged for {component_key}: {new_version}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error refreshing version for {component_key}: {e}")
            return False
    
    def get_all_versions(self) -> Dict[str, dict]:
        """Get version information for all components"""
        return {key: comp['version_info'].to_dict() for key, comp in self.components.items()}
    
    def get_components_info(self) -> List[dict]:
        """
        Get component information in the format expected by system_info
        """
        result = []
        
        for key, comp in self.components.items():
            # Map component keys to display names
            result.append({
                "name": comp['version_info'].name,
                "running": self.get_component_running(key),
                "current_version": comp['version_info'].current_version,
                "latest_version": comp['version_info'].latest_version or comp['version_info'].current_version,
                "update_available": comp['version_info'].update_available,
                "last_checked": comp['version_info'].last_checked.isoformat() if comp['version_info'].last_checked else None,
                "release_notes": comp['version_info'].release_notes,
                "release_url": comp['version_info'].release_url
            })
        
        return result
    
    async def _wait_for_status(self, request_id: str, timeout: int = 600) -> Optional[dict]:
        """Wait for status response from coordinator"""
        status_file = self.update_status_dir / f"{request_id}.json"
        start_time = time.time()
        
        logger.info(f"Polling for status: {status_file}")
        
        while time.time() - start_time < timeout:
            if status_file.exists():
                try:
                    with open(status_file, 'r') as f:
                        status = json.load(f)
                    
                    # Clean up status file
                    status_file.unlink()
                    
                    logger.info(f"Received status for request {request_id}")
                    return status
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in status file: {e}")
                    return None
                except Exception as e:
                    logger.error(f"Error reading status file: {e}")
                    return None
            
            # Poll every second
            await asyncio.sleep(1)
        
        logger.warning(f"Timeout waiting for status {request_id}")
        return None


