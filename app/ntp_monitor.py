#!/usr/bin/env python3
"""
NTP Monitor for DuneBugger Remote
Monitors NTP server availability and notifies other components of status changes
"""

import time
import socket
import asyncio
from dunebugger_logging import logger
from dunebugger_settings import settings


class NTPMonitor:
    """
    Monitors NTP availability and notifies components when status changes
    """
    
    def __init__(self, system_info_model):
        """
        Initialize NTP Monitor
        
        Args:
            system_info_model: SystemInfoModel instance for NTP checking
        """
        self.system_info_model = system_info_model
        self.messaging_queue_handler = None
        self.websocket_message_handler = None
        self._monitor_task = None
        
        # NTP configuration
        self._ntp_servers = settings.ntpServers
        self._ntp_timeout = settings.ntpTimeout
        logger.info(f"NTP Monitor initialized with servers: {self._ntp_servers}, timeout: {self._ntp_timeout}s")
    
    def set_messaging_queue_handler(self, messaging_queue_handler):
        """Set the messaging queue handler for sending scheduler notifications"""
        self.messaging_queue_handler = messaging_queue_handler
    
    async def start_monitoring(self):
        """Start the NTP availability monitoring task"""
        if self._monitor_task is None:
            self._monitor_task = asyncio.create_task(self._monitoring_loop())
            logger.info("NTP availability monitoring started")
        else:
            logger.warning("NTP monitoring already running")
    
    async def stop_monitoring(self):
        """Stop the NTP availability monitoring task"""
        if self._monitor_task is not None:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
            logger.info("NTP availability monitoring stopped")
    
    async def send_ntp_status_to_scheduler(self):
        """Send current NTP status to scheduler (called on request)"""
        current_state = self.system_info_model.is_ntp_available()
        await self._notify_scheduler_ntp_status(current_state)
        logger.debug(f"NTP status sent to scheduler on request: {current_state}")
    
    def check_ntp_availability(self) -> bool:
        """
        Check if NTP is available by querying configured NTP servers
        Returns True if at least one NTP server is reachable
        """
        if not self._ntp_servers:
            logger.warning("No NTP servers configured")
            return False
        
        for ntp_server in self._ntp_servers:
            try:
                # NTP packet format: LI (2 bits) | VN (3 bits) | Mode (3 bits)
                # LI=0, VN=3 (NTPv3), Mode=3 (client)
                ntp_packet = b'\x1b' + 47 * b'\0'
                
                # Create socket with timeout
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(self._ntp_timeout)
                
                # Send packet to NTP server (port 123)
                sock.sendto(ntp_packet, (ntp_server, 123))
                
                # Receive response
                data, address = sock.recvfrom(1024)
                sock.close()
                
                if data:
                    logger.debug(f"NTP server {ntp_server} is reachable")
                    return True
                    
            except socket.timeout:
                logger.debug(f"NTP server {ntp_server} timeout")
            except socket.gaierror as e:
                logger.debug(f"NTP server {ntp_server} DNS resolution failed: {e}")
            except Exception as e:
                logger.debug(f"NTP server {ntp_server} error: {e}")
        
        # No server was reachable
        logger.warning("No NTP servers are reachable")
        return False
    
    async def _monitoring_loop(self):
        """Monitor NTP availability at configured intervals"""
        # Initial check and notification
        previous_state = None
        current_state = self.check_ntp_availability()
        self.system_info_model.set_ntp_available(current_state)
        
        # Send initial NTP status to scheduler
        await self._notify_scheduler_ntp_status(current_state)
        previous_state = current_state
        
        while True:
            try:
                # Wait for the configured interval
                await asyncio.sleep(settings.ntpCheckIntervalSecs)
                
                # Check NTP availability
                current_state = self.check_ntp_availability()
                self.system_info_model.set_ntp_available(current_state)
                
                # Detect state change
                if previous_state is not None and current_state != previous_state:
                    logger.warning(f"NTP availability changed: {previous_state} -> {current_state}")
                    
                    # Send system info update on state change
                    self.websocket_message_handler.send_ntp_status()
                    
                    # Notify scheduler about NTP status change
                    await self._notify_scheduler_ntp_status(current_state)
                
                previous_state = current_state
                
            except asyncio.CancelledError:
                logger.info("NTP monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in NTP monitoring loop: {e}")
                # Continue the loop even if there's an error
                await asyncio.sleep(settings.ntpCheckIntervalSecs)
    
    async def _notify_scheduler_ntp_status(self, ntp_available: bool):
        """
        Notify the scheduler about NTP availability status
        
        Args:
            ntp_available: Boolean indicating if NTP is available
        """
        try:
            if self.messaging_queue_handler and self.messaging_queue_handler.mqueue_sender:
                await self.messaging_queue_handler.dispatch_message(
                    {
                        "ntp_available": ntp_available,
                    },
                    "ntp_status",
                    "scheduler"
                )
                logger.info(f"NTP status update sent to scheduler: ntp_available={ntp_available}")
            else:
                logger.warning("Cannot send NTP status to scheduler - messaging queue not available")
        except Exception as e:
            logger.error(f"Error sending NTP status to scheduler: {e}")
