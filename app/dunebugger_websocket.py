import threading
import time
import os
import random
import asyncio
import atexit
from azure.messaging.webpubsubclient import WebPubSubClient
from azure.messaging.webpubsubclient.models import CallbackType, WebPubSubDataType
from dunebugger_logging import logger
from dunebugger_settings import settings
class WebPubSubListener:
    def __init__(self, internet_monitor, auth_client, ws_message_handler):
        self.wss_url = ""
        self.client = None
        self.internet_monitor = internet_monitor
        self.auth_client = auth_client
        self.ws_message_handler = ws_message_handler
        self.group_name = os.getenv("WS_GROUP_NAME")
        self.broadcastEnabled = settings.broadcastInitialState
        self.stop_event = threading.Event()
        # Store reference to the main event loop for use in callback methods
        self.main_event_loop = None
        # Internet connectivity state tracking
        self.connection_retry_scheduled = False
        self.should_be_connected = False  # Track if we want to be connected

        atexit.register(self.stop)
        
        # Register callbacks with internet monitor
        self.internet_monitor.add_connected_callback(self._on_internet_connected)
        self.internet_monitor.add_disconnected_callback(self._on_internet_disconnected)
        
        time.sleep(2)  # Allow some time for the internet check to initialize

    async def _setup_client(self):
        """Setup the WebSocket client with event subscriptions."""
        self.update_auth()
        self.client = WebPubSubClient(self.wss_url, auto_rejoin_groups=True, autoReconnect=True, reconnect_retry_total=2)
        self.client.subscribe(CallbackType.CONNECTED, lambda e: self._on_websocket_connected(e))
        self.client.subscribe(
            CallbackType.DISCONNECTED,
            lambda e: self._handle_websocket_disconnection(e),
        )
        self.client.subscribe(CallbackType.STOPPED, lambda: logger.debug("Websocket client stopped"))
        self.client.subscribe(CallbackType.GROUP_MESSAGE, self._on_message_received)
        self.client.subscribe(CallbackType.SERVER_MESSAGE, self._on_message_received)
        self.client.subscribe(CallbackType.REJOIN_GROUP_FAILED, lambda e: self._handle_rejoin_failure(e))

    async def start(self):
        # Store the current event loop for later use in callbacks
        self.main_event_loop = asyncio.get_running_loop()

        """Start the WebSocket connection if internet is available."""
        self.should_be_connected = True
        
        # Check if internet is available before attempting connection
        if not self.internet_monitor.get_connection_status():
            logger.warning("Cannot start WebSocket: No internet connection available")
            logger.info("WebSocket will start automatically when internet connection is restored")
            return
        
        await self._attempt_connection()

    async def _attempt_connection(self):
        """Internal method to attempt WebSocket connection."""
        logger.debug("Attempting WebSocket connection...")
        
        try:
            # Clean up any existing client
            if self.client:
                try:
                    self.client.close()
                except:
                    pass  # Ignore errors during cleanup
                self.client = None
            
            # Setup new client
            await self._setup_client()
            
            # Open connection
            logger.debug("Opening WebSocket connection...")
            self.client.open()
            
            # Join group
            logger.debug(f"Joining group: {self.group_name}")
            self.client.join_group(self.group_name)
            
            logger.info(f"Successfully joined group: {self.group_name}")
            
            # Send heartbeat
            self.ws_message_handler.dispatch_message("Is anyone there?", "heartbeat", "broadcast")
            
        except Exception as e:
            logger.error(f"Failed to establish WebSocket connection: {e}")
            
            # Clean up failed client
            if self.client:
                try:
                    self.client.close()
                except:
                    pass
                self.client = None
            
            # Schedule retry if conditions are right
            if self.internet_monitor.get_connection_status() and self.should_be_connected:
                logger.info("Scheduling WebSocket connection retry due to failure")
                self._schedule_connection_retry(delay=15)
            
            #raise  # Re-raise to let caller know it failed

    def _handle_rejoin_failure(self, e):
        logger.error(f"Failed to rejoin group {e.group}: {e.error}")
        time.sleep(3)
        self.client.join_group(e.group)

    def _handle_websocket_disconnection(self, e):
        """Handle WebSocket disconnection with internet connectivity awareness."""
        logger.debug(f"Websocket disconnected {e.connection_id}")
        
        # Check if disconnection is due to internet loss
        if not self.internet_monitor.get_connection_status():
            logger.info("WebSocket disconnection due to internet connectivity loss")
            # Don't attempt to reconnect until internet is restored
        elif self.should_be_connected:
            # Internet is available but WebSocket disconnected - schedule retry
            logger.warning("WebSocket disconnected while internet is available - scheduling reconnection")
            self._schedule_connection_retry(delay=5)

    def update_auth(self):
        self.auth_client._update_user_info()
        self.wss_url = self.auth_client.wss_url

    def stop(self):
        """Stops all monitoring threads and closes the WebSocket connection."""
        self.should_be_connected = False
        self.stop_event.set()
        
        # Remove callbacks from internet monitor
        try:
            self.internet_monitor.remove_connected_callback(self._on_internet_connected)
            self.internet_monitor.remove_disconnected_callback(self._on_internet_disconnected)
        except Exception as e:
            logger.debug(f"Error removing internet monitor callbacks: {e}")
        
        if self.client:
            self.client.close()

    def _on_internet_connected(self):
        """Callback when internet connection is restored."""
        logger.info("Internet connection restored - WebSocket will attempt to reconnect")
        
        if not self.should_be_connected:
            logger.debug("WebSocket should not be connected, skipping reconnection")
            return
            
        # Try to get the current event loop or use the stored one
        try:
            current_loop = None
            try:
                current_loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop in current thread
                current_loop = self.main_event_loop
            
            if current_loop and not current_loop.is_closed():
                # Schedule reconnection in the event loop
                asyncio.run_coroutine_threadsafe(self._handle_internet_reconnection(), current_loop)
            else:
                # Fallback: use threading approach
                logger.warning("No available event loop, using threaded reconnection")
                self._schedule_connection_retry(delay=2)
                
        except Exception as e:
            logger.error(f"Error scheduling WebSocket reconnection: {e}")
            # Fallback to threaded retry
            self._schedule_connection_retry(delay=5)

    def _on_internet_disconnected(self):
        """Callback when internet connection is lost."""
        logger.warning("Internet connection lost - WebSocket connection will be affected")
        # The WebSocket client will handle the disconnection automatically
        # We just need to ensure we don't try to reconnect until internet is back

    async def _handle_internet_reconnection(self):
        """Handle reconnection when internet is restored."""
        logger.info("Starting WebSocket reconnection process...")
        
        if not self.should_be_connected:
            logger.debug("WebSocket should not be connected, aborting reconnection")
            return
            
        # Wait a moment for network to stabilize
        logger.debug("Waiting for network to stabilize...")
        await asyncio.sleep(3)
        
        # Double-check internet connectivity
        if not self.internet_monitor.get_connection_status():
            logger.warning("Internet connection lost again during reconnection attempt")
            return
        
        # Check if we're already connected
        if self.client and self.client.is_connected():
            logger.info("WebSocket already connected, no reconnection needed")
            return
            
        # Attempt to reconnect
        logger.info("Attempting to reconnect WebSocket after internet restoration")
        try:
            await self._attempt_connection()
            logger.info("WebSocket reconnection attempt completed")
        except Exception as e:
            logger.error(f"Failed to reconnect WebSocket: {e}")
            # Schedule another retry
            if self.should_be_connected and self.internet_monitor.get_connection_status():
                logger.info("Scheduling another reconnection attempt")
                self._schedule_connection_retry(delay=10)

    def _schedule_connection_retry(self, delay=10):
        """Schedule a connection retry after a delay."""
        if self.connection_retry_scheduled:
            logger.debug("Connection retry already scheduled, skipping")
            return
            
        self.connection_retry_scheduled = True
        logger.info(f"Scheduling WebSocket connection retry in {delay} seconds")
        
        def retry_connection():
            try:
                logger.debug(f"Starting retry connection after {delay}s delay")
                time.sleep(delay)
                
                # Reset the retry flag
                self.connection_retry_scheduled = False
                
                # Check if we should still try to connect
                if not self.should_be_connected:
                    logger.debug("Should not be connected anymore, aborting retry")
                    return
                
                if not self.internet_monitor.get_connection_status():
                    logger.debug("Internet not available, aborting retry")
                    return
                
                # Try to get current event loop
                try:
                    current_loop = asyncio.get_running_loop()
                    if current_loop and not current_loop.is_closed():
                        asyncio.run_coroutine_threadsafe(self._attempt_connection(), current_loop)
                        return
                except RuntimeError:
                    pass
                
                # Try using stored loop
                if self.main_event_loop and not self.main_event_loop.is_closed():
                    asyncio.run_coroutine_threadsafe(self._attempt_connection(), self.main_event_loop)
                else:
                    logger.error("No available event loop for retry connection")
                    
            except Exception as e:
                logger.error(f"Error in retry connection thread: {e}")
                # Reset flag so we can try again
                self.connection_retry_scheduled = False
        
        # Run retry in a separate thread
        retry_thread = threading.Thread(target=retry_connection, daemon=True, name="WebSocket-Retry")
        retry_thread.start()

    def _on_websocket_connected(self, e):
        """Handle WebSocket connection established."""
        logger.info(f"Connected: {e.connection_id}")
        
        # Send system info on connection
        try:
            self.ws_message_handler.send_system_info()
        except Exception as exc:
            logger.error(f"Failed to send system info on connection: {exc}")

    def _on_message_received(self, e):
        """Handle received messages synchronously."""
        if e.data.get("subject") not in ["heartbeat"] or random.random() <= 1:  # 0.05:
            logger.debug(f"Message received from group {e.group}: {e.data}")

        # Use run_coroutine_threadsafe to run the async handler in the main event loop
        # This avoids the "no running event loop" error
        if self.main_event_loop and self.main_event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self.handle_message(e.data), self.main_event_loop)
        else:
            logger.error("Cannot process message: No running event loop available")

    async def handle_message(self, message):
        """Process the message asynchronously in the main event loop context."""
        try:
            # Handle the message using the message handler
            await self.ws_message_handler.process_websocket_message(message)
        except Exception as exc:
            logger.error(f"Error processing message: {exc}")

    def send_log(self, message):
        self.ws_message_handler.send_log(message)

    def enable_broadcast(self):
        self.broadcastEnabled = True

    def disable_broadcast(self):
        self.broadcastEnabled = False

    def send_message(self, message):
        # Check internet connectivity before attempting to send
        if not self.internet_monitor.get_connection_status():
            logger.debug("Cannot send message: No internet connection")
            return
            
        if self.client and self.client.is_connected():
            try:
                if self.broadcastEnabled is True:
                    self.client.send_to_group(self.group_name, message, WebPubSubDataType.JSON, no_echo=True)
                    # Too chatty: uncomment only for detailed tracing
                    #if message["subject"] not in ["heartbeat", "gpio_state"] or random.random() <= 1:  # 0.05:
                    #    logger.debug(f"Sending websocket message to group {self.group_name}: {str(message)[:20]}")
                else:
                    logger.debug("Broadcasting is disabled.")
            except Exception as e:
                logger.error(f"Failed to send message to group ${self.group_name}: {e}")
                # Check if failure is due to internet connectivity
                if not self.internet_monitor.get_connection_status():
                    logger.info("Message send failure may be due to internet connectivity loss")
        else:
            if settings.websocketEnabled is True:
                if not self.internet_monitor.get_connection_status():
                    logger.debug("Cannot send message: No internet connection")
                else:
                    logger.warning("Cannot send message, WebSocket is disconnected.")
            else:
                logger.debug("Cannot send message, WebSocket is not enabled.")
