#!/usr/bin/env python3
"""
Hardware Information Helper
Collects hardware-related system information
"""

import os
import platform
import psutil
from typing import Dict, Any, Optional
from dunebugger_logging import logger


class HardwareInfoHelper:
    def __init__(self):
        pass
    
    def get_hardware_info(self) -> Dict[str, Any]:
        """
        Collect comprehensive hardware information
        """
        try:
            return {
                "model": self._get_hardware_model(),
                "revision": self._get_hardware_revision(),
                "cpu": self._get_cpu_info(),
                "memory": self._get_memory_info(),
                "storage": self._get_storage_info()
            }
        except Exception as e:
            logger.error(f"Error collecting hardware info: {e}")
            return self._get_minimal_hardware_info()
    
    def _get_hardware_model(self) -> str:
        """
        Get hardware model information
        """
        try:
            # Try to get Raspberry Pi model info
            if os.path.exists('/proc/device-tree/model'):
                with open('/proc/device-tree/model', 'r') as f:
                    model = f.read().strip('\x00').strip()
                    if model:
                        return model
        except Exception as e:
            logger.debug(f"Could not read device tree model: {e}")
        
        # Fallback to platform info
        try:
            return platform.machine() or "Unknown"
        except Exception:
            return "Unknown"
    
    def _get_hardware_revision(self) -> str:
        """
        Get hardware revision
        """
        try:
            # Try to get Raspberry Pi revision
            if os.path.exists('/proc/cpuinfo'):
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if line.startswith('Revision'):
                            revision = line.split(':')[1].strip()
                            return revision
        except Exception as e:
            logger.debug(f"Could not read revision from cpuinfo: {e}")
        
        return "Unknown"
    
    def _get_cpu_info(self) -> Dict[str, Any]:
        """
        Get CPU information
        """
        try:
            cpu_info = {
                "model": self._get_cpu_model(),
                "cores": psutil.cpu_count(logical=False) or psutil.cpu_count(),
                "architecture": platform.machine(),
                "current_temp_c": self._get_cpu_temperature(),
                "load": list(os.getloadavg()) if hasattr(os, 'getloadavg') else [0.0, 0.0, 0.0]
            }
            return cpu_info
        except Exception as e:
            logger.error(f"Error getting CPU info: {e}")
            return {
                "model": "Unknown",
                "cores": 1,
                "architecture": platform.machine(),
                "current_temp_c": None,
                "load": [0.0, 0.0, 0.0]
            }
    
    def _get_cpu_model(self) -> str:
        """
        Get CPU model name
        """
        try:
            if os.path.exists('/proc/cpuinfo'):
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if line.startswith('model name') or line.startswith('Model'):
                            model = line.split(':')[1].strip()
                            if model:
                                return model
        except Exception as e:
            logger.debug(f"Could not read CPU model from cpuinfo: {e}")
        
        return "Unknown CPU"
    
    def _get_cpu_temperature(self) -> Optional[float]:
        """
        Get CPU temperature in Celsius
        """
        try:
            # Try common temperature paths
            temp_paths = [
                '/sys/class/thermal/thermal_zone0/temp',
                '/sys/devices/virtual/thermal/thermal_zone0/temp'
            ]
            
            for path in temp_paths:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        temp_str = f.read().strip()
                        # Temperature is usually in millidegrees
                        temp = float(temp_str) / 1000.0
                        return round(temp, 1)
        except Exception as e:
            logger.debug(f"Could not read CPU temperature: {e}")
        
        return None
    
    def _get_memory_info(self) -> Dict[str, int]:
        """
        Get memory information
        """
        try:
            memory = psutil.virtual_memory()
            return {
                "total_mb": round(memory.total / (1024 * 1024)),
                "used_mb": round(memory.used / (1024 * 1024))
            }
        except Exception as e:
            logger.error(f"Error getting memory info: {e}")
            return {
                "total_mb": 0,
                "used_mb": 0
            }
    
    def _get_storage_info(self) -> Dict[str, Any]:
        """
        Get storage information
        """
        try:
            # Get root filesystem usage
            usage = psutil.disk_usage('/')
            
            # Try to get root device name
            root_device = self._get_root_device()
            
            return {
                "root_device": root_device,
                "total_gb": round(usage.total / (1024 * 1024 * 1024), 1),
                "used_gb": round(usage.used / (1024 * 1024 * 1024), 1)
            }
        except Exception as e:
            logger.error(f"Error getting storage info: {e}")
            return {
                "root_device": "Unknown",
                "total_gb": 0,
                "used_gb": 0
            }
    
    def _get_root_device(self) -> str:
        """
        Get the root device name
        """
        try:
            # Try to get from mount info
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == '/':
                        return parts[0]
        except Exception as e:
            logger.debug(f"Could not determine root device: {e}")
        
        return "Unknown"
    
    def _get_minimal_hardware_info(self) -> Dict[str, Any]:
        """
        Return minimal hardware info in case of errors
        """
        return {
            "model": "Unknown",
            "revision": "Unknown",
            "cpu": {
                "model": "Unknown",
                "cores": 1,
                "architecture": platform.machine(),
                "current_temp_c": None,
                "load": [0.0, 0.0, 0.0]
            },
            "memory": {
                "total_mb": 0,
                "used_mb": 0
            },
            "storage": {
                "root_device": "Unknown",
                "total_gb": 0,
                "used_gb": 0
            }
        }