import time
import threading
from dunebugger_logging import logger


class MessageHandler:
    def __init__(self, heartBeatEverySecs, heartBeatLoopDurationSecs):
        self.websocket_client = None
        self.messaging_queue_handler = None
        self.heartBeatEverySecs = heartBeatEverySecs
        self.heartBeatLoopDurationSecs = heartBeatLoopDurationSecs
        self.countdown_timer = 0
        self.alive_message = {
            "body": "I am alive",
            "subject": "heartbeat",
            "source": "controller",
            "destination": "broadcast",
        }
        self.heartbeat_event = threading.Event()
        self.countdown_event = threading.Event()
        threading.Thread(target=self._send_heartbeat, daemon=True).start()
        threading.Thread(target=self._countdown, daemon=True).start()

    async def process_websocket_message(self, websocket_message):
        try:
            subject = websocket_message["subject"]

            if subject in ["heartbeat"]:
                self.websocket_client.send_message(self.alive_message)
                self.handle_heartbeat()
            elif subject in ["dunebugger_set"]:
                await self.messaging_queue_handler.mqueue_sender.send(websocket_message, "core")
            elif subject in ["refresh"]:
                await self.messaging_queue_handler.mqueue_sender.send(websocket_message, "core")
                await self.messaging_queue_handler.mqueue_sender.send(websocket_message, "scheduler")
            else:
                logger.warning(f"Unknown subject: {subject}. Ignoring message.")

        except KeyError as key_error:
            logger.error(f"KeyError: {key_error}. Message: {websocket_message}")
        except Exception as e:
            logger.error(f"Error processing message: {e}. Message: {websocket_message}")

    # def handle_request_sequence(self, sequence, connection_id="broadcast"):
    #     self.dispatch_message("self.sequence_handler.get_sequence(sequence)", "sequence", connection_id)

    def dispatch_message(self, message_body, subject, connection_id="broadcast"):
        data = {
            "body": message_body,
            "subject": subject,
            "source": "controller",
            "destination": connection_id,
        }
        self.websocket_client.send_message(data)

    def _send_heartbeat(self):
        while True:
            self.heartbeat_event.wait()  # Wait until the event is set
            self.websocket_client.send_message(self.alive_message)
            time.sleep(self.heartBeatEverySecs)

    def _countdown(self):
        while True:
            self.countdown_event.wait()  # Wait until the event is set
            if self.countdown_timer > 0:
                time.sleep(1)
                self.countdown_timer -= 1
            elif self.countdown_timer == 0:
                self.dispatch_message("Is anyone there?", "heartbeat", "broadcast")
                self.heartbeat_event.clear()  # Stop heartbeat loop until reactivated
                self.countdown_event.clear()  # Stop countdown loop until reactivated

    def handle_heartbeat(self):
        self.countdown_timer = self.heartBeatLoopDurationSecs
        self.heartbeat_event.set()  # Activate heartbeat loop
        self.countdown_event.set()  # Activate countdown loop

    def send_log(self, log_message):
        data = {"body": log_message, "subject": "log", "source": "controller"}
        self.websocket_client.send_message(data)
