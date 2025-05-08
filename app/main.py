#!/usr/bin/env python3
import time
import asyncio
from dunebugger_settings import settings
from class_factory import websocket_client, mqueue
from dunebugger_logging import logger

async def main():
    await mqueue.start()
    if settings.websocketEnabled is True:
        await websocket_client.start()

    try:
        logger.info("Listening for messages. Press Ctrl+C to exit.")
        while True:
            await asyncio.sleep(0.1)  # Keep the main thread alive
    except KeyboardInterrupt:
        logger.info("Shutting down...")

if __name__ == "__main__":
    asyncio.run(main())
    logger.info("Main thread finished.")
