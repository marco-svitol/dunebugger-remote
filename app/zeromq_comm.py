import zmq
import threading
import time

class ZeroMQComm:
    def __init__(self, mode, address="ipc:///tmp/dunebugger-core", topic=""):
        """
        Initialize the ZeroMQ communication module.
        
        :param mode: 'REQ' for request-response or 'SUB' for subscription.
        :param address: The ZeroMQ address (default: IPC socket).
        :param topic: Topic for PUB/SUB mode (default: empty for all topics).
        """
        self.context = zmq.Context()
        self.mode = mode
        self.topic = topic
        self.socket = None
        self.listener_thread = None
        self.stop_event = threading.Event()

        if mode == "REQ":
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect(address)
        elif mode == "SUB":
            self.socket = self.context.socket(zmq.SUB)
            self.socket.connect(address)
            self.socket.setsockopt_string(zmq.SUBSCRIBE, topic)
        elif mode == "PUB":
            self.socket = self.context.socket(zmq.PUB)
            self.socket.bind(address)
        else:
            raise ValueError("Invalid mode. Use 'REQ', 'SUB', or 'PUB'.")

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

    def start_listener(self, callback):
        """
        Start a listener thread to process incoming messages.
        
        :param callback: A function to handle received messages.
        """
        if self.mode not in ["SUB", "REQ"]:
            raise RuntimeError("Listener is only supported in SUB or REQ mode.")

        def listen():
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

        self.listener_thread = threading.Thread(target=listen, daemon=True)
        self.listener_thread.start()

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