#!/usr/bin/env python3
from dunebugger_settings import settings
from class_factory import websocket_client, mqueue_listener
from dunebugger_logging import logger
import time


def main():
    # Start the listener with the callback
    mqueue_listener.start_listener()
    if settings.websocketEnabled is True:
        websocket_client.start()

    try:
        logger.info("Listening for messages. Press Ctrl+C to exit.")
        while True:
            time.sleep(0.1)  # Keep the main thread alive
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    main()
