import json
from dunebugger_logging import logger


class MessagingQueueHandler:
    """Class to handle messaging queue operations."""

    def __init__(self, websocket_message_handler):
        self.mqueue_sender = None
        self.websocket_message_handler = websocket_message_handler

    async def process_mqueue_message(self, mqueue_message):
        """Callback method to process received messages."""
        # Parse the JSON string back into a dictionary
        try:
            data = mqueue_message.data.decode()
            message_json = json.loads(data)
        except (AttributeError, UnicodeDecodeError) as decode_error:
            logger.error(f"Failed to decode message data: {decode_error}. Raw message: {mqueue_message.data}")
            return
        except json.JSONDecodeError as json_error:
            logger.error(f"Failed to parse message as JSON: {json_error}. Raw message: {data}")
            return

        try:
            subject = (mqueue_message.subject).split(".")[2]
            logger.debug(f"Processing message: {str(message_json)[:20]}. Subject: {subject}. Reply to: {mqueue_message.reply}")

            if subject in ["gpio_state", "sequence_state", "sequence", "playing_time", "log"]:
                self.websocket_message_handler.dispatch_message(message_json["body"], message_json["subject"])
            else:
                logger.warning(f"Unknown subjcet: {subject}. Ignoring message.")
        except KeyError as key_error:
            logger.error(f"KeyError: {key_error}. Message: {message_json}")
        except Exception as e:
            logger.error(f"Error processing message: {e}. Message: {message_json}")
