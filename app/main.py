#!/usr/bin/env python3
from dunebugger_settings import settings
from class_factory import websocket_client
from zeromq_comm import ZeroMQComm
import time
def handle_message(message):
    """Callback function to process received messages."""
    print(f"Received message: {message}")

def main():

    if settings.remoteEnabled == True:
        websocket_client.start()

    communication = ZeroMQComm(
        mode="REQ",
        address="ipc:///tmp/dunebugger-core",
        # topic=settings.zmqTopic,
    )

    # Start the listener with the callback
    communication.start_listener(callback=handle_message)

    try:
        print("Listening for messages. Press Ctrl+C to exit.")
        while True:
            time.sleep(1)  # Keep the main thread alive
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        communication.close()

if __name__ == "__main__":
    main()
