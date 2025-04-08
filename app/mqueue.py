import zmq
import threading
import atexit
import json
from dunebugger_logging import logger

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
        self.send_lock = threading.Lock()  # Lock to ensure thread safety
        atexit.register(self.close)

    def connect(self):
        if self.mode == "REQ":
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect(self.address)
        elif self.mode == "REP":
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(self.address)
        else:
            raise ValueError("Invalid mode. Use 'REQ' or 'REP'.")

    def send(self, message, timeout=5000):
        """
        Send a request and wait for a reply (REQ mode) with a timeout.

        :param message: The message to send.
        :param timeout: Timeout in milliseconds to wait for a reply (default: 5000ms).
        :return: The reply received from the server.
        :raises: RuntimeError if the mode is not REQ, if a timeout occurs, or if the socket is not ready.
        """
        if self.mode != "REQ":
            raise RuntimeError("send is only supported in REQ mode.")

        with self.send_lock:  # Ensure thread safety
            # Set the receive timeout
            self.socket.setsockopt(zmq.RCVTIMEO, timeout)

            compact_message = json.dumps(message, separators=(",", ":"))
            logger.debug(f"Sending message: {compact_message}")  # Debug log

            try:
                self.socket.send_string(compact_message)
                reply = self.socket.recv_string()  # Wait for a reply with the specified timeout
                logger.debug(f"Received reply: {reply}")  # Debug log
                return reply
            except zmq.error.Again:
                #raise RuntimeError(f"Timeout occurred after {timeout}ms while waiting for a reply.")
                logger.error(f"Timeout occurred after {timeout}ms while waiting for a reply.")
                self._reset_socket()
    
    def listen(self):
        """
        Listen for incoming messages and send a reply (REP mode).
        """
        if self.mode != "REP":
            raise RuntimeError("listen is only supported in REP mode.")
        
        print(f"Listening for messages on {self.address}...")
        while not self.stop_event.is_set():
            try:
                # Wait for a request
                message = self.socket.recv_string()
                print(f"Received message: {message}")  # Debug log
                # Process the message and generate a reply
                json_message = json.loads(message)
                reply = self.mqueue_handler.process_message(json_message)
                # Send the reply
                self.socket.send_string(reply)
                print(f"Sent reply: {reply}")  # Debug log
            except zmq.ZMQError as e:
                if not self.stop_event.is_set():
                    print(f"ZeroMQ error: {e}")
            except Exception as e:
                print(f"Error in listener: {e}")

    def start_listener(self):
        """
        Start the listener thread for REP mode.
        """
        if self.mode != "REP":
            raise RuntimeError("Listener is only supported in REP mode.")
        
        self.listener_thread = threading.Thread(target=self.listen, daemon=True)
        self.listener_thread.start()

    def stop_listener(self):
        """Stop the listener thread."""
        self.stop_event.set()
        if self.listener_thread:
            self.listener_thread.join()

    def _reset_socket(self):
        """
        Reset the ZeroMQ socket after an error or timeout.
        """
        logger.warning("Resetting the ZeroMQ socket...")
        if self.socket:
            self.socket.close()  # Close the current socket
        self.connect()  # Recreate and reconnect the socket
        
    def close(self):
        """Close the ZeroMQ socket and terminate the context."""
        self.stop_listener()
        if self.socket:
            self.socket.close()
        self.context.term()
