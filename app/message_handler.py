import threading
from dunebuggerlogging import logger
from dunebugger_settings import settings

class MessageHandler:
    def __init__(self):
        """
        Initialize the MessageHandler.

        Parameters:
        - state_tracker (StateTracker): The state tracker instance to monitor.
        - check_interval (int): The interval (in seconds) to check for state changes.
        """
        self.websocket_client = None
        # self.pipe_listener = None
        # self.state_tracker = None
        # self.sequence_handler = None
        self.check_interval = int(settings.stateCheckIntervalSecs)

    def process_message(self, message):
        message_type = message.get("type")
        connection_id = message.get("connectionId")
        if message_type == "request_gpio_state":
            self.handle_request_gpio_state(connection_id)
        elif message_type == "request_sequence_state":
            self.handle_request_sequence_state(connection_id)
        elif message_type == "request_sequence":
            sequence = message.get("body")
            self.handle_request_sequence(sequence, connection_id)
        elif message_type == "ping":
            self.handle_ping(connection_id)
        elif message_type == "command":
            command = message.get("body")
            "self.pipe_listener.pipe_send(command)"
        else:
            logger.warning(f"Unknown messsage type: {message_type}")

    def handle_request_gpio_state(self, connection_id = "broadcast"):
        self.dispatch_message(
            "mygpio_handler.get_gpio_status()",
            "gpio_state",
            connection_id)

    def handle_request_sequence_state(self, connection_id = "broadcast"):
        self.dispatch_message(
            "self.sequence_handler.get_state()",
            "sequence_state",
            connection_id
        )

    def handle_request_playing_time(self, connection_id = "broadcast"):
        self.dispatch_message(
            "self.sequence_handler.get_playing_time()",
            "playing_time",
            connection_id
        )
        
    def handle_request_sequence(self, sequence, connection_id = "broadcast"):
        self.dispatch_message(
            "self.sequence_handler.get_sequence(sequence)",
            "sequence",
            connection_id
        )

    def dispatch_message(self, message_body, response_type, connection_id = "broadcast"):
        data = {
            "body": message_body,
            "type": response_type,
            "source": "controller",
            "destination": connection_id,
        }
        self.websocket_client.send_message(data)

    def handle_ping(self, connection_id = "broadcast"):
        data = {
            "body": "pong",
            "type": "ping",
            "source": "controller",
            "destination": connection_id,
        }
        self.websocket_client.send_message(data)

    def send_log(self, log_message):
        data = {
            "body": log_message,
            "type": "log",
            "source": "controller"
        }
        self.websocket_client.send_message(data)
