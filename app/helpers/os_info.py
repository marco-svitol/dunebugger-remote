#!/usr/bin/env python3
"""
Operating System Information Helper
Collects OS-related system information
"""

import os
import platform
import subprocess
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from dunebugger_logging import logger


class OSInfoHelper:
    def __init__(self):
        pass
    
    def get_os_info(self) -> Dict[str, Any]:
        """
        Collect comprehensive OS information
        """
        try:
            return {
                "name": self._get_os_name(),
                "version": self._get_os_version(),
                "kernel": self._get_kernel_version(),
                "boot_time_utc": self._get_boot_time()
            }
        except Exception as e:
            logger.error(f"Error collecting OS info: {e}")
            return self._get_minimal_os_info()
    
    def _get_os_name(self) -> str:
        """
        Get OS name and distribution
        """
        try:
            # Try to read from os-release file (most Linux distributions)
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release', 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        if line.startswith('PRETTY_NAME='):
                            name = line.split('=', 1)[1].strip().strip('"\'')
                            return name
            
            # Try LSB release
            if os.path.exists('/etc/lsb-release'):
                with open('/etc/lsb-release', 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        if line.startswith('DISTRIB_DESCRIPTION='):
                            name = line.split('=', 1)[1].strip().strip('"\'')
                            return name
            
            # Fallback to platform
            return platform.system()
            
        except Exception as e:
            logger.debug(f"Could not determine OS name: {e}")
            return platform.system()
    
    def _get_os_version(self) -> str:
        """
        Get OS version information
        """
        try:
            # Try to read from os-release file
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release', 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        if line.startswith('VERSION='):
                            version = line.split('=', 1)[1].strip().strip('"\'')
                            return version
                        elif line.startswith('VERSION_ID='):
                            version_id = line.split('=', 1)[1].strip().strip('"\'')
                            return version_id
            
            # Try debian version
            if os.path.exists('/etc/debian_version'):
                with open('/etc/debian_version', 'r') as f:
                    version = f.read().strip()
                    return f"Debian {version}"
            
            # Fallback to platform
            return platform.release()
            
        except Exception as e:
            logger.debug(f"Could not determine OS version: {e}")
            return platform.release()
    
    def _get_kernel_version(self) -> str:
        """
        Get kernel version
        """
        try:
            return platform.release()
        except Exception as e:
            logger.debug(f"Could not determine kernel version: {e}")
            return "Unknown"
    
    def _get_boot_time(self) -> str:
        """
        Get system boot time in UTC
        """
        try:
            # Try to get boot time from /proc/stat
            if os.path.exists('/proc/stat'):
                with open('/proc/stat', 'r') as f:
                    for line in f:
                        if line.startswith('btime'):
                            boot_timestamp = int(line.split()[1])
                            boot_time = datetime.fromtimestamp(boot_timestamp, tz=timezone.utc)
                            return boot_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # Fallback: try using uptime command
            try:
                result = subprocess.run(['uptime', '-s'], 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=5)
                if result.returncode == 0:
                    boot_time_str = result.stdout.strip()
                    # Parse the uptime format and convert to UTC
                    boot_time = datetime.strptime(boot_time_str, "%Y-%m-%d %H:%M:%S")
                    # Assume local time and convert to UTC (approximate)
                    boot_time_utc = boot_time.replace(tzinfo=timezone.utc)
                    return boot_time_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError) as e:
                logger.debug(f"Could not get boot time from uptime command: {e}")
            
            # Last resort: estimate based on current time minus uptime
            try:
                with open('/proc/uptime', 'r') as f:
                    uptime_seconds = float(f.read().split()[0])
                    boot_time = datetime.now(timezone.utc) - timedelta(seconds=uptime_seconds)
                    return boot_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception as e:
                logger.debug(f"Could not calculate boot time from uptime: {e}")
            
        except Exception as e:
            logger.error(f"Error getting boot time: {e}")
        
        return "Unknown"
    
    def _get_minimal_os_info(self) -> Dict[str, str]:
        """
        Return minimal OS info in case of errors
        """
        return {
            "name": platform.system(),
            "version": "Unknown",
            "kernel": platform.release(),
            "boot_time_utc": "Unknown"
        }