from dunebugger_logging import logger


class MessagingQueueHandler:
    """Class to handle messaging queue operations."""

    def __init__(self, websocket_message_handler):
        self.mqueue_sender = None
        self.websocket_message_handler = websocket_message_handler

    def process_message(self, message):
        """Callback method to process received messages."""
        logger.debug(f"Received message: {message}")
        return "OK"
