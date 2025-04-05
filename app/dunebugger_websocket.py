import threading
import time
import os
import socket
import random
from azure.messaging.webpubsubclient import WebPubSubClient
from azure.messaging.webpubsubclient.models import CallbackType, WebPubSubDataType
from dunebuggerlogging import logger
from dunebugger_settings import settings

class WebPubSubListener:
    def __init__(self):
        self.wss_url = ""
        self.client = None
        self.auth_client = None
        self.message_handler = None
        self.group_name = os.getenv("WS_GROUP_NAME")
        self.broadcastEnabled = settings.broadcastInitialState
        self.stop_event = threading.Event()
        self.internet_available = True
        self.internet_check_thread = threading.Thread(target=self._monitor_internet, daemon=True)
        self.websocket_monitor_thread = threading.Thread(target=self._monitor_websocket, daemon=True)
        self.internet_check_thread.start()
        time.sleep(2)  # Allow some time for the internet check to initialize
        # self.websocket_monitor_thread.start()

    def _setup_client(self):
        """Setup the WebSocket client with event subscriptions."""
        self.update_auth()
        self.client = WebPubSubClient(self.wss_url, auto_rejoin_groups=True, autoReconnect=True, reconnect_retry_total=2)
        self.client.subscribe(CallbackType.CONNECTED, lambda e: logger.info(f"Connected: {e.connection_id}"))
        self.client.subscribe(
            CallbackType.DISCONNECTED,
            lambda e: logger.debug(f"Websocket disconnected {e.connection_id}"),
        )
        self.client.subscribe(CallbackType.STOPPED, lambda: logger.debug("Websocket client stopped"))
        self.client.subscribe(CallbackType.GROUP_MESSAGE, self._on_message_received)
        self.client.subscribe(CallbackType.SERVER_MESSAGE, self._on_message_received)
        self.client.subscribe(CallbackType.REJOIN_GROUP_FAILED, lambda e: self._handle_rejoin_failure(e))

    def _monitor_internet(self):
        """Continuously check if the internet is available."""
        while not self.stop_event.is_set():
            was_available = self.internet_available
            self.internet_available = self._check_internet()
            if self.internet_available and not was_available:
                logger.info("Internet restored, attempting WebSocket restart...")
                self._restart()
            time.sleep(5)  # Check every 5 seconds

    def _monitor_websocket(self):
        """Ensure the WebSocket connection stays active when the internet is available."""
        while not self.stop_event.is_set():
            if self.internet_available:
                if not self.client or not self.client.is_connected:
                    logger.warning("Internet is available, but WebSocket is disconnected. Attempting to reconnect...")
                    self._restart()
            time.sleep(10)  # Check every 10 seconds

    def _check_internet(self, host="8.8.8.8", port=53, timeout=3):
        """Check internet connectivity by attempting to reach a public DNS server."""
        try:
            socket.create_connection((host, port), timeout)
            return True
        except OSError:
            return False

    def start(self):
        if self.internet_available:
            try:
                self._setup_client()
                self.client.open()
                if not self.websocket_monitor_thread.is_alive():
                    self.websocket_monitor_thread.start()
                self.client.join_group(self.group_name)
                logger.info(f"Joined group: {self.group_name}")
            except Exception as e:
                logger.error(f"Failed to start WebSocket: {e}")
        else:
            logger.warning("Internet is not available. WebSocket connection skipped.")

    def _restart(self):
        logger.warning("Restarting WebSocket connection...")
        # self._setup_client()
        self.start()

    def _handle_rejoin_failure(self, e):
        logger.error(f"Failed to rejoin group {e.group}: {e.error}")
        time.sleep(3)
        self.client.join_group(e.group)

    def update_auth(self):
        self.auth_client._update_user_info()
        self.wss_url = self.auth_client.wss_url
        logger.debug(self.wss_url)
        # self.group_name = self.auth_client.user_id

    def stop(self):
        """Stops all monitoring threads and closes the WebSocket connection."""
        self.stop_event.set()
        if self.client:
            self.client.close()

    def _on_message_received(self, e):
        if e.data.get("type") not in ["ping", "pong"]  or random.random() < 0.05:
            logger.debug(f"Message received from group {e.group}: {e.data}")
        """Handle received messages."""
        self.handle_message(e.data)

    def handle_message(self, message):
        self.message_handler.process_message(message)

    def send_log(self, message):
        self.message_handler.send_log(message)
    
    def enable_broadcast(self):
        self.broadcastEnabled = True

    def disable_broadcast(self):
        self.broadcastEnabled = False

    def send_message(self, message):
        if self.client and self.client.is_connected:
            try:
                if self.broadcastEnabled == True:
                    self.client.send_to_group(self.group_name, message, WebPubSubDataType.JSON, no_echo=True)
                    if message.get("type") not in ["ping", "pong", "gpio_state"] or random.random() < 0.05:
                        logger.debug(f"Sending message to group {self.group_name}: {message}")
                else:
                    logger.debug("Broadcasting is disabled.")
            except Exception as e:
                logger.error(f"Failed to send message to group ${self.group_name}: {e}")
        else:
            if settings.remoteEnabled == True: 
                logger.warning("Cannot send message, WebSocket is disconnected.")
            else:
                logger.debug("Cannot send message, WebSocket is not enabled.")
