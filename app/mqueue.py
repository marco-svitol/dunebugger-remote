import zmq
import threading
import atexit


class ZeroMQComm:
    def __init__(self, mode, address, mqueue_handler, topic=""):
        """
        Initialize the ZeroMQ communication module.

        :param mode: 'REQ' for request-response or 'SUB' for subscription.
        :param address: The ZeroMQ address (default: IPC socket).
        :param topic: Topic for PUB/SUB mode (default: empty for all topics).
        """
        self.context = zmq.Context()
        self.mode = mode
        self.address = address
        self.topic = topic
        self.socket = None
        self.connect()
        self.listener_thread = None
        self.mqueue_handler = mqueue_handler
        self.stop_event = threading.Event()
        atexit.register(self.close)

    def connect(self):
        if self.mode == "REQ":
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect(self.address)
        elif self.mode == "SUB":
            self.socket = self.context.socket(zmq.SUB)
            self.socket.connect(self.address)
            self.socket.setsockopt_string(zmq.SUBSCRIBE, self.topic)
        elif self.mode == "PUB":
            self.socket = self.context.socket(zmq.PUB)
            self.socket.bind(self.address)
        else:
            raise ValueError("Invalid mode. Use 'REQ', 'SUB', or 'PUB'.")

    def listen(self, callback):
        while not self.stop_event.is_set():
            try:
                # Use poller to avoid busy-waiting
                poller = zmq.Poller()
                poller.register(self.socket, zmq.POLLIN)
                events = dict(poller.poll(timeout=1000))  # Wait for 1 second
                if self.socket in events and events[self.socket] == zmq.POLLIN:
                    message = self.socket.recv_string()
                    callback(message)
            except zmq.ZMQError as e:
                if not self.stop_event.is_set():
                    print(f"ZeroMQ error: {e}")
            except Exception as e:
                print(f"Error in listener thread: {e}")

    def start_listener(self):
        """
        Start a listener thread to process incoming messages.

        :param callback: A function to handle received messages.
        """
        if self.mode not in ["SUB", "REQ"]:
            raise RuntimeError("Listener is only supported in SUB or REQ mode.")

        self.listener_thread = threading.Thread(target=self.listen, args=(self.mqueue_handler,), daemon=True)
        self.listener_thread.start()

    def send_message(self, message):
        """
        Send a message to the server (for REQ or PUB mode).

        :param message: The message to send.
        """
        if self.mode in ["REQ", "PUB"]:
            self.socket.send_string(message)
        else:
            raise RuntimeError("send_message is not supported in SUB mode.")

    def receive_message(self):
        """
        Receive a message from the server (for REQ or SUB mode).

        :return: The received message as a string.
        """
        if self.mode in ["REQ", "SUB"]:
            return self.socket.recv_string()
        else:
            raise RuntimeError("receive_message is not supported in PUB mode.")

    def stop_listener(self):
        """Stop the listener thread."""
        self.stop_event.set()
        if self.listener_thread:
            self.listener_thread.join()

    def close(self):
        """Close the ZeroMQ socket and terminate the context."""
        self.stop_listener()
        self.socket.close()
        self.context.term()
