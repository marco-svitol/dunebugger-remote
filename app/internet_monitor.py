import threading
import time
import socket
import urllib.request
import urllib.error
from typing import Callable, Optional
from dunebugger_logging import logger


class InternetConnectionMonitor:
    """
    Monitors internet connectivity continuously and notifies listeners when connection state changes.
    
    Uses multiple methods to detect internet connectivity:
    1. DNS resolution test
    2. HTTPs connectivity test
    """
    
    def __init__(self, test_domain, check_interval: int = 30, timeout: int = 2):
        """
        Initialize the internet connection monitor.
        
        Args:
            check_interval: Seconds between connectivity checks
            timeout: Timeout for connectivity tests in seconds
        """
        self.test_domain = test_domain
        self.check_interval = check_interval
        self.timeout = timeout
        self.is_connected = False
        self.is_monitoring = False
        self.monitor_thread = None
        self.stop_event = threading.Event()
        
        # Callbacks for connection state changes
        self.on_connected_callbacks = []
        self.on_disconnected_callbacks = []
        
        # Lock for thread-safe operations
        self._lock = threading.Lock()
        
        logger.info(f"Internet monitor initialized with {check_interval}s check interval")
    
    def add_connected_callback(self, callback: Callable[[], None]):
        """Add callback to be called when internet connection is established."""
        with self._lock:
            self.on_connected_callbacks.append(callback)
            logger.debug(f"Added connected callback: {callback.__name__ if hasattr(callback, '__name__') else str(callback)}")
    
    def add_disconnected_callback(self, callback: Callable[[], None]):
        """Add callback to be called when internet connection is lost."""
        with self._lock:
            self.on_disconnected_callbacks.append(callback)
            logger.debug(f"Added disconnected callback: {callback.__name__ if hasattr(callback, '__name__') else str(callback)}")
    
    def remove_connected_callback(self, callback: Callable[[], None]):
        """Remove a connected callback."""
        with self._lock:
            if callback in self.on_connected_callbacks:
                self.on_connected_callbacks.remove(callback)
                logger.debug(f"Removed connected callback: {callback.__name__ if hasattr(callback, '__name__') else str(callback)}")
    
    def remove_disconnected_callback(self, callback: Callable[[], None]):
        """Remove a disconnected callback."""
        with self._lock:
            if callback in self.on_disconnected_callbacks:
                self.on_disconnected_callbacks.remove(callback)
                logger.debug(f"Removed disconnected callback: {callback.__name__ if hasattr(callback, '__name__') else str(callback)}")
    
    def _check_dns_resolution(self) -> bool:
        """Check internet connectivity by resolving DNS."""
        try:
            # Try to resolve a well-known domain name (not IP)
            socket.setdefaulttimeout(self.timeout)
            socket.gethostbyname(self.test_domain)
            return True
        except (socket.gaierror, socket.timeout, OSError):
            return False
        finally:
            socket.setdefaulttimeout(None)
    
    def _check_http_request(self) -> bool:
        """Check internet connectivity by making an actual HTTP request."""
        urls = [
            f'https://{self.test_domain}'
        ]
        
        for url in urls:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'DuneBugger-Monitor/1.0'})
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    if response.getcode() == 200:
                        return True
            except (urllib.error.URLError, urllib.error.HTTPError, socket.timeout, OSError):
                continue
        
        return False
    
    def check_connection(self) -> bool:
        """
        Perform a comprehensive internet connectivity check.
        
        Returns:
            True if internet connection is available, False otherwise
        """
        # Try DNS resolution first (fastest and most reliable)
        dns_result = self._check_dns_resolution()
        logger.debug(f"DNS resolution check: {dns_result}")
        
        if dns_result:
            # DNS works, but let's verify with a http connection
            http_req_result = self._check_http_request()
            logger.debug(f"HTTP request check: {http_req_result}")
            if http_req_result:
                return True
        
        logger.debug("All connectivity checks failed")
        return False
    
    def _notify_connected(self):
        """Notify all callbacks that internet connection is established."""
        with self._lock:
            callbacks = self.on_connected_callbacks.copy()
        
        for callback in callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in connected callback {callback}: {e}")
    
    def _notify_disconnected(self):
        """Notify all callbacks that internet connection is lost."""
        with self._lock:
            callbacks = self.on_disconnected_callbacks.copy()
        
        for callback in callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in disconnected callback {callback}: {e}")
    
    def _monitor_loop(self):
        """Main monitoring loop that runs in a separate thread."""
        logger.info("Internet connection monitoring started")
        
        while not self.stop_event.is_set():
            try:
                current_status = self.check_connection()
                
                # Check if status changed
                if current_status != self.is_connected:
                    logger.info(f"Internet connection status changed: {self.is_connected} -> {current_status}")
                    self.is_connected = current_status
                    
                    if current_status:
                        logger.info("Internet connection established")
                        self._notify_connected()
                    else:
                        logger.warning("Internet connection lost")
                        self._notify_disconnected()
                else:
                    # Log periodic status (less frequently to avoid spam)
                    if time.time() % (self.check_interval * 4) < self.check_interval:
                        logger.debug(f"Internet connection status: {'Connected' if current_status else 'Disconnected'}")
                
                # Wait for next check or stop signal
                if self.stop_event.wait(self.check_interval):
                    break
                    
            except Exception as e:
                logger.error(f"Error in internet monitor loop: {e}")
                # Continue monitoring even if there's an error
                if self.stop_event.wait(5):  # Short wait before retry
                    break
        
        logger.info("Internet connection monitoring stopped")
    
    def start_monitoring(self):
        """Start the internet connection monitoring in a background thread."""
        if self.is_monitoring:
            logger.warning("Internet monitoring is already running")
            return
        
        # Perform initial check
        self.is_connected = self.check_connection()
        logger.info(f"Initial internet connection status: {'Connected' if self.is_connected else 'Disconnected'}")
        
        # Start monitoring thread
        self.stop_event.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.is_monitoring = True
        
        logger.info("Internet connection monitoring thread started")
    
    def stop_monitoring(self):
        """Stop the internet connection monitoring."""
        if not self.is_monitoring:
            logger.debug("Internet monitoring is not running")
            return
        
        logger.info("Stopping internet connection monitoring...")
        self.stop_event.set()
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=10)
            if self.monitor_thread.is_alive():
                logger.warning("Monitor thread did not stop gracefully")
        
        self.is_monitoring = False
        logger.info("Internet connection monitoring stopped")
    
    def get_connection_status(self) -> bool:
        """Get the current internet connection status."""
        return self.is_connected
    
    def force_check(self) -> bool:
        """Force an immediate connectivity check and update status."""
        logger.debug("Forcing immediate connectivity check")
        new_status = self.check_connection()
        
        if new_status != self.is_connected:
            logger.info(f"Connection status changed: {self.is_connected} -> {new_status}")
            old_status = self.is_connected
            self.is_connected = new_status
            
            # Notify callbacks
            if new_status and not old_status:
                self._notify_connected()
            elif not new_status and old_status:
                self._notify_disconnected()
        
        return new_status
    
    def wait_for_connection(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for internet connection to be established.
        
        Args:
            timeout: Maximum time to wait in seconds. None for no timeout.
            
        Returns:
            True if connection is established within timeout, False otherwise
        """
        start_time = time.time()
        
        while True:
            if self.is_connected:
                return True
            
            if timeout and (time.time() - start_time) >= timeout:
                return False
            
            time.sleep(1)
