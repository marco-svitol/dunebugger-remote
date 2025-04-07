from dunebuggger_logging import logger


class MessageHandler:
    def __init__(self):
        self.websocket_client = None
        self.messaging_queue_handler = None

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

    def handle_request_gpio_state(self, connection_id="broadcast"):
        self.dispatch_message("mygpio_handler.get_gpio_status()", "gpio_state", connection_id)

    def handle_request_sequence_state(self, connection_id="broadcast"):
        self.dispatch_message("self.sequence_handler.get_state()", "sequence_state", connection_id)

    def handle_request_playing_time(self, connection_id="broadcast"):
        self.dispatch_message("self.sequence_handler.get_playing_time()", "playing_time", connection_id)

    def handle_request_sequence(self, sequence, connection_id="broadcast"):
        self.dispatch_message("self.sequence_handler.get_sequence(sequence)", "sequence", connection_id)

    def dispatch_message(self, message_body, response_type, connection_id="broadcast"):
        data = {
            "body": message_body,
            "type": response_type,
            "source": "controller",
            "destination": connection_id,
        }
        self.websocket_client.send_message(data)

    # TODO: send broadcast pong after receiving ping.
    # Continue to send ping every 30 seconds
    # A countdown of 10 minutes should start when the first ping is received
    # if countdown reaches 0, stop sending ping and send a "are you alive" message
    # if no response is received from the "are you alive" message, stop sending ping
    def handle_ping(self, connection_id="broadcast"):
        data = {
            "body": "pong",
            "type": "ping",
            "source": "controller",
            "destination": connection_id,
        }
        self.websocket_client.send_message(data)

    def send_log(self, log_message):
        data = {"body": log_message, "type": "log", "source": "controller"}
        self.websocket_client.send_message(data)
