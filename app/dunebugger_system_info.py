#!/usr/bin/env python3
"""
System Info Model for DuneBugger Remote
Collects and structures system information for transmission to remote systems
"""

from datetime import datetime, timezone
from typing import Dict, Any
from dunebugger_logging import logger
from dunebugger_settings import settings
from helpers.hardware_info import HardwareInfoHelper
from helpers.os_info import OSInfoHelper
from helpers.network_info import NetworkInfoHelper

class SystemInfoModel:
    def __init__(self):
        self.device_id = settings.deviceID
        self.hardware_helper = HardwareInfoHelper()
        self.os_helper = OSInfoHelper()
        self.network_helper = NetworkInfoHelper()
        self.component_updater = None  # Will be set by class_factory
        
        # NTP availability (managed by NTPMonitor)
        self._ntp_available = False
    
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
                    "dunebugger_components": self.component_updater.get_components_info(),
                    "hardware": self.hardware_helper.get_hardware_info(),
                    "os": self.os_helper.get_os_info(),
                    "network": self.network_helper.get_network_info(),
                    "location": self._get_location_info()
                }
            }
        except Exception as e:
            logger.error(f"Error collecting system info: {e}")
            return self._get_minimal_system_info()
    
    def _get_location_info(self) -> Dict[str, str]:
        """
        Get location information
        """
        return {
            "description": settings.locationDescription
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

