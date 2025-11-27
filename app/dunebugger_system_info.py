#!/usr/bin/env python3
"""
System Info Model for DuneBugger Remote
Collects and structures system information for transmission to remote systems
"""

import os
import subprocess
from datetime import datetime, timezone
from typing import Dict, Any
from dunebugger_logging import logger
from helpers.hardware_info import HardwareInfoHelper
from helpers.os_info import OSInfoHelper
from helpers.network_info import NetworkInfoHelper


class SystemInfoModel:
    def __init__(self):
        self.device_id = os.getenv("DEVICE_ID", "Environment Variable DEVICE_ID Not Set")
        self.hardware_helper = HardwareInfoHelper()
        self.os_helper = OSInfoHelper()
        self.network_helper = NetworkInfoHelper()
        
    def get_system_info(self) -> Dict[str, Any]:
        """
        Collect and return comprehensive system information
        """
        try:
            return {
                "system_info": {
                    "device_id": self.device_id,
                    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
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
        # Get dunebugger component state from systemctl
        dunebugger_state = self._get_service_state("dunebugger.service")
        
        return [
            {
                "name": "dunebugger",
                "state": dunebugger_state
            },
            {
                "name": "dunebugger-remote",
                "state": "running"  # Always running since this is the service providing the answer
            }
        ]
    
    def _get_service_state(self, service_name: str) -> str:
        """
        Get the state of a systemctl service
        """
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            # systemctl is-active returns "active" for running services
            state = result.stdout.strip()
            
            # Map systemctl states to our expected states
            if state == "active":
                return "running"
            elif state == "inactive":
                return "stopped"
            elif state == "failed":
                return "failed"
            else:
                return state  # Return whatever systemctl reports
                
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout checking service state for {service_name}")
            return "unknown"
        except Exception as e:
            logger.error(f"Error checking service state for {service_name}: {e}")
            return "unknown"
    
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
    
    def create_websocket_message(self) -> Dict[str, Any]:
        """
        Create a websocket message with system info
        """
        system_info = self.get_system_info()
        return {
            "body": system_info,
            "subject": "system_info",
            "source": "controller",
            "destination": "broadcast"
        }