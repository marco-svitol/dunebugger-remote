#!/usr/bin/env python3
"""
System Info Model for DuneBugger Remote
Collects and structures system information for transmission to remote systems
"""

import os
import time
from datetime import datetime, timezone
from typing import Dict, Any
from dunebugger_logging import logger
from helpers.hardware_info import HardwareInfoHelper
from helpers.os_info import OSInfoHelper
from helpers.network_info import NetworkInfoHelper
from version import get_version_info

class SystemInfoModel:
    def __init__(self):
        self.device_id = os.getenv("DEVICE_ID", "Environment Variable DEVICE_ID Not Set")
        self.hardware_helper = HardwareInfoHelper()
        self.os_helper = OSInfoHelper()
        self.network_helper = NetworkInfoHelper()
        
        # Heartbeat core flag with TTL (45 seconds)
        self._heartbeat_core_alive = False
        self._heartbeat_core_timestamp = 0
        self._core_full_version = ""
        self._heartbeat_ttl = 45  # seconds
        
        # Heartbeat scheduler flag with TTL (45 seconds)
        self._heartbeat_scheduler_alive = False
        self._heartbeat_scheduler_timestamp = 0
        self._scheduler_full_version = ""
        
        # NTP availability (managed by NTPMonitor)
        self._ntp_available = False
    
    def set_heartbeat_core_alive(self, version_info):
        """Set the heartbeat core flag to alive and update timestamp"""
        self._heartbeat_core_alive = True
        self._heartbeat_core_timestamp = time.time()
        self._core_full_version = version_info.get("full_version", "not available")
        logger.debug(f"Heartbeat core flag set to alive. Version: {self._core_full_version}")
    
    def set_heartbeat_scheduler_alive(self, version_info):
        """Set the heartbeat scheduler flag to alive and update timestamp"""
        self._heartbeat_scheduler_alive = True
        self._heartbeat_scheduler_timestamp = time.time()
        self._scheduler_full_version = version_info.get("full_version", "not available")
        logger.debug(f"Heartbeat scheduler flag set to alive. Version: {self._scheduler_full_version}")
    
    def is_heartbeat_core_alive(self) -> bool:
        """Check if the heartbeat core flag is alive (within TTL)"""
        if not self._heartbeat_core_alive:
            return False
        
        current_time = time.time()
        if current_time - self._heartbeat_core_timestamp > self._heartbeat_ttl:
            self._heartbeat_core_alive = False
            logger.debug("Heartbeat core flag expired (TTL exceeded)")
            return False
        
        return True
    
    def is_heartbeat_scheduler_alive(self) -> bool:
        """Check if the heartbeat scheduler flag is alive (within TTL)"""
        if not self._heartbeat_scheduler_alive:
            return False
        
        current_time = time.time()
        if current_time - self._heartbeat_scheduler_timestamp > self._heartbeat_ttl:
            self._heartbeat_scheduler_alive = False
            logger.debug("Heartbeat scheduler flag expired (TTL exceeded)")
            return False
        
        return True
    
    def set_ntp_available(self, available: bool):
        """Set the NTP availability status (called by NTPMonitor)"""
        self._ntp_available = available
        logger.debug(f"NTP availability set to: {available}")
    
    def is_ntp_available(self) -> bool:
        """Return the current NTP availability status"""
        return self._ntp_available
        
    def get_system_info(self) -> Dict[str, Any]:
        """
        Collect and return comprehensive system information
        """
        try:
            return {
                "system_info": {
                    "device_id": self.device_id,
                    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
                    "ntp_available": self._ntp_available,
                    "dunebugger_components": self._get_component_info(),
                    "hardware": self.hardware_helper.get_hardware_info(),
                    "os": self.os_helper.get_os_info(),
                    "network": self.network_helper.get_network_info(),
                    "location": self._get_location_info()
                }
            }
        except Exception as e:
            logger.error(f"Error collecting system info: {e}")
            return self._get_minimal_system_info()
    
    def _get_component_info(self) -> list:
        """
        Get information about DuneBugger components
        """
        # Use heartbeat flags to determine component states
        dunebugger_state = "running" if self.is_heartbeat_core_alive() else "not_responding"
        scheduler_state = "running" if self.is_heartbeat_scheduler_alive() else "not_responding"
        
        return [
            {
                "name": "Dunebugger",
                "state": dunebugger_state,
                "version": self._core_full_version,
                "last_available_version" : self._core_full_version
            },
            {
                "name": "Scheduler",
                "state": scheduler_state,
                "version": self._scheduler_full_version,
                "last_available_version" : "1.0.1"
            },
            {
                "name": "Remote",
                "state": "running",  # Always running since this is the service providing the answer
                "version": get_version_info()['full_version'] ,
                "last_available_version" : "1.0.3"
            }
        ]
    

    
    def _get_location_info(self) -> Dict[str, str]:
        """
        Get location information
        """
        default_description = "Environment Variable LOCATION_DESCRIPTION Not Set"
        return {
            "description": os.getenv("LOCATION_DESCRIPTION", default_description)
        }
    
    def _get_minimal_system_info(self) -> Dict[str, Any]:
        """
        Return minimal system info in case of errors
        """
        return {
            "system_info": {
                "device_id": self.device_id,
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
                "status": "error_collecting_info"
            }
        }

