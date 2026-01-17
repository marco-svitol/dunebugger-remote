#!/usr/bin/env python3
import asyncio
import signal
import sys

# print component version info on startup
from version import get_version_info
print(f"Dunebugger core version: {get_version_info()['full_version']}, build type: {get_version_info()['build_type']}, build number: {get_version_info()['build_number']}")

from dunebugger_settings import settings
from class_factory import websocket_client, mqueue, websocket_message_handler, ntp_monitor, component_updater
from dunebugger_logging import logger


# Global flag for shutdown
shutdown_event = asyncio.Event()


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_event.set()


async def main():
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    await mqueue.start_listener()
    if settings.websocketEnabled is True:
        await websocket_client.start()
    
    # Start core heartbeat monitoring
    await websocket_message_handler.start_components_heartbeat()
    
    # Start NTP availability monitoring
    await ntp_monitor.start_monitoring()
    
    # Start periodic update checking
    await component_updater.start_periodic_check()

    try:
        logger.info("Listening for messages. Press Ctrl+C to exit.")
        # Wait for shutdown event instead of infinite loop
        await shutdown_event.wait()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received...")
    finally:
        logger.info("Shutting down...")
        await component_updater.stop_periodic_check()
        await ntp_monitor.stop_monitoring()
        await mqueue.close_listener()
        if settings.websocketEnabled is True:
            await websocket_client.close()


if __name__ == "__main__":
    asyncio.run(main())
    logger.info("Main thread finished.")
