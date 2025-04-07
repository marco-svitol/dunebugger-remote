from dunebuggger_logging import logger


class MessagingQueueHandler:
    """Class to handle messaging queue operations."""

    def __init__(self, websocket_message_handler):
        self.mqueue_client = None
        self.websocket_message_handler = websocket_message_handler

    def handle_message(message):
        """Callback method to process received messages."""
        logger.debug(f"Received message: {message}")
