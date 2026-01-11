import json
from dunebugger_logging import logger


class MessagingQueueHandler:
    """Class to handle messaging queue operations."""

    def __init__(self, websocket_message_handler):
        self.mqueue_sender = None
        self.websocket_message_handler = websocket_message_handler
        self.ntp_monitor = None

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
            logger.debug(f"Processing message: {message_json}. Subject: {subject}. Reply to: {mqueue_message.reply}")

            if subject == "heartbeat" and message_json.get("source") == "core":
                # Handle heartbeat reply from dunebugger core
                self.websocket_message_handler.system_info_model.set_heartbeat_core_alive()
            elif subject == "heartbeat" and message_json.get("source") == "scheduler":
                # Handle heartbeat reply from dunebugger scheduler
                self.websocket_message_handler.system_info_model.set_heartbeat_scheduler_alive()
            elif subject == "get_ntp_status" and message_json.get("source") == "scheduler":
                # Handle NTP status request from scheduler
                if self.ntp_monitor:
                    await self.ntp_monitor.send_ntp_status_to_scheduler()
                    logger.debug("NTP status request processed from scheduler")
                else:
                    logger.warning("NTP monitor not available to handle get_ntp_status request from scheduler")
            elif subject in ["gpio_state", "sequence_state", "sequence", "playing_time", "log", "current_schedule", "next_actions", "last_executed_action", "scheduler_status", "modes_list", "analytics_metrics"]:
                self.websocket_message_handler.dispatch_message(message_json["body"], message_json["subject"])
            else:
                logger.warning(f"Unknown subject: {subject}. Ignoring message.")
        except KeyError as key_error:
            logger.error(f"KeyError: {key_error}. Message: {message_json}")
        except Exception as e:
            logger.error(f"Error processing message: {e}. Message: {message_json}")

        return f"Processed message with subject: {subject}"
