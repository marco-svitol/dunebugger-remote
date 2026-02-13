#!/usr/bin/env python3
"""
Network Information Helper
Collects network-related system information
"""

import os
import socket
import subprocess
import psutil
from typing import Dict, Any, List, Optional
from dunebugger_logging import logger


class NetworkInfoHelper:
    def __init__(self):
        self.is_docker = self._is_running_in_docker()
    
    def get_network_info(self) -> Dict[str, Any]:
        """
        Collect comprehensive network information
        """
        try:
            return {
                "hostname": self._get_hostname(),
                "interfaces": self._get_network_interfaces(),
                "connectivity": self._get_connectivity_info()
            }
        except Exception as e:
            logger.error(f"Error collecting network info: {e}")
            return self._get_minimal_network_info()
    
    def _get_hostname(self) -> str:
        """
        Get system hostname
        """
        try:
            return socket.gethostname()
        except Exception as e:
            logger.debug(f"Could not get hostname: {e}")
            return "unknown"
    
    def _get_network_interfaces(self) -> List[Dict[str, Any]]:
        """
        Get information about network interfaces
        """
        interfaces = []
        
        try:
            # Get network interface statistics and addresses
            net_if_addrs = psutil.net_if_addrs()
            net_if_stats = psutil.net_if_stats()
            
            for interface_name, addresses in net_if_addrs.items():
                # Skip loopback interface
                if interface_name == 'lo':
                    continue
                
                # Skip Docker-related interfaces when running in Docker with host networking
                if self.is_docker and self._is_docker_interface(interface_name):
                    continue
                
                interface_info = {
                    "name": interface_name,
                    "type": self._get_interface_type(interface_name),
                    "mac": None,
                    "ip_v4": None,
                    "ip_v6": None,
                    "state": "unknown"
                }
                
                # Extract addresses
                for addr in addresses:
                    if addr.family == psutil.AF_LINK:  # MAC address
                        interface_info["mac"] = addr.address
                    elif addr.family == socket.AF_INET:  # IPv4
                        interface_info["ip_v4"] = addr.address
                    elif addr.family == socket.AF_INET6:  # IPv6
                        # Skip link-local addresses (they start with fe80::)
                        if not addr.address.startswith('fe80::'):
                            interface_info["ip_v6"] = addr.address
                        elif interface_info["ip_v6"] is None:
                            # Keep link-local as fallback
                            interface_info["ip_v6"] = addr.address
                
                # Get interface statistics
                if interface_name in net_if_stats:
                    stats = net_if_stats[interface_name]
                    interface_info["state"] = "up" if stats.isup else "down"
                    
                    # Try to get speed (not always available)
                    if hasattr(stats, 'speed') and stats.speed > 0:
                        interface_info["speed_mbps"] = stats.speed
                
                # Add WiFi-specific information
                if interface_info["type"] == "wifi":
                    wifi_info = self._get_wifi_info(interface_name)
                    interface_info.update(wifi_info)
                
                interfaces.append(interface_info)
                
        except Exception as e:
            logger.error(f"Error getting network interfaces: {e}")
        
        return interfaces
    
    def _get_interface_type(self, interface_name: str) -> str:
        """
        Determine interface type based on name
        """
        interface_name_lower = interface_name.lower()
        
        if interface_name_lower.startswith(('wlan', 'wifi', 'wlp')):
            return "wifi"
        elif interface_name_lower.startswith(('eth', 'enp', 'ens')):
            return "ethernet"
        elif interface_name_lower.startswith('usb'):
            return "usb"
        elif interface_name_lower.startswith('ppp'):
            return "ppp"
        else:
            return "other"
    
    def _get_wifi_info(self, interface_name: str) -> Dict[str, Any]:
        """
        Get WiFi-specific information
        """
        wifi_info = {
            "ssid": None,
            "signal_strength_dbm": None
        }
        
        try:
            # Try to get WiFi info using iwconfig
            result = subprocess.run(['iwconfig', interface_name], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            
            if result.returncode == 0:
                output = result.stdout
                
                # Parse SSID
                if 'ESSID:' in output:
                    essid_line = [line for line in output.split('\n') if 'ESSID:' in line]
                    if essid_line:
                        essid_part = essid_line[0].split('ESSID:')[1].strip()
                        if essid_part and essid_part != 'off/any':
                            wifi_info["ssid"] = essid_part.strip('"')
                
                # Parse signal strength
                if 'Signal level=' in output:
                    signal_line = [line for line in output.split('\n') if 'Signal level=' in line]
                    if signal_line:
                        signal_part = signal_line[0].split('Signal level=')[1].split()[0]
                        try:
                            # Remove 'dBm' suffix if present
                            signal_value = signal_part.replace('dBm', '').strip()
                            wifi_info["signal_strength_dbm"] = int(signal_value)
                        except ValueError:
                            pass
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.debug(f"Could not get WiFi info for {interface_name}: {e}")
        
        return wifi_info
    
    def _get_connectivity_info(self) -> Dict[str, Any]:
        """
        Get network connectivity information
        """
        connectivity = {
            "default_route": None,
            "dns_servers": [],
            "internet_reachable": False,
            "latency_ms_to_gateway": None
        }
        
        try:
            # Get default route
            connectivity["default_route"] = self._get_default_gateway()
            
            # Get DNS servers
            connectivity["dns_servers"] = self._get_dns_servers()
            
            # Test internet connectivity
            connectivity["internet_reachable"] = self._test_internet_connectivity()
            
            # Test latency to gateway
            if connectivity["default_route"]:
                connectivity["latency_ms_to_gateway"] = self._ping_gateway(connectivity["default_route"])
            
        except Exception as e:
            logger.error(f"Error getting connectivity info: {e}")
        
        return connectivity
    
    def _get_default_gateway(self) -> Optional[str]:
        """
        Get the default gateway IP address
        """
        try:
            # Try using ip route command
            result = subprocess.run(['ip', 'route', 'show', 'default'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            
            if result.returncode == 0:
                output = result.stdout.strip()
                if output:
                    # Parse: "default via 192.168.1.1 dev eth0 ..."
                    parts = output.split()
                    if 'via' in parts:
                        via_index = parts.index('via')
                        if via_index + 1 < len(parts):
                            return parts[via_index + 1]
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.debug(f"Could not get default gateway: {e}")
        
        return None
    
    def _get_dns_servers(self) -> List[str]:
        """
        Get list of DNS servers
        """
        dns_servers = []
        
        try:
            # Read from /etc/resolv.conf
            if os.path.exists('/etc/resolv.conf'):
                with open('/etc/resolv.conf', 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('nameserver'):
                            parts = line.split()
                            if len(parts) >= 2:
                                dns_servers.append(parts[1])
            
        except Exception as e:
            logger.debug(f"Could not read DNS servers: {e}")
        
        return dns_servers
    
    def _test_internet_connectivity(self) -> bool:
        """
        Test if internet is reachable
        """
        try:
            # Try to connect to a reliable public DNS server
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('8.8.8.8', 53))
            sock.close()
            return result == 0
        except Exception as e:
            logger.debug(f"Internet connectivity test failed: {e}")
            return False
    
    def _ping_gateway(self, gateway_ip: str) -> Optional[float]:
        """
        Ping the gateway and return latency in milliseconds
        """
        try:
            # Use ping command with single packet
            ping_cmd = ['ping', '-c', '1', '-W', '2', gateway_ip]
            result = subprocess.run(ping_cmd, 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            
            if result.returncode == 0:
                output = result.stdout
                # Parse ping output for time
                for line in output.split('\n'):
                    if 'time=' in line:
                        time_part = line.split('time=')[1].split()[0]
                        try:
                            latency = float(time_part.replace('ms', ''))
                            return round(latency, 1)
                        except ValueError:
                            pass
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.debug(f"Could not ping gateway {gateway_ip}: {e}")
        
        return None
    
    def _is_running_in_docker(self) -> bool:
        """
        Check if we are running inside a Docker container
        """
        try:
            # Check for .dockerenv file (created by Docker)
            if os.path.exists('/.dockerenv'):
                return True
            
            # Check cgroup for docker
            with open('/proc/1/cgroup', 'r') as f:
                return 'docker' in f.read()
        except Exception:
            return False
    
    def _is_docker_interface(self, interface_name: str) -> bool:
        """
        Check if an interface is Docker-related and should be filtered out
        """
        docker_prefixes = [
            'docker',     # Docker bridge interfaces
            'br-',        # Docker bridge interfaces
            'veth',       # Virtual ethernet pairs used by Docker
        ]
        
        interface_lower = interface_name.lower()
        return any(interface_lower.startswith(prefix) for prefix in docker_prefixes)
    
    def _get_minimal_network_info(self) -> Dict[str, Any]:
        """
        Return minimal network info in case of errors
        """
        return {
            "hostname": self._get_hostname(),
            "interfaces": [],
            "connectivity": {
                "default_route": None,
                "dns_servers": [],
                "internet_reachable": False,
                "latency_ms_to_gateway": None
            }
        }