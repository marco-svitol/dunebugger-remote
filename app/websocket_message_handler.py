import time
import threading
import asyncio
from dunebugger_logging import logger
from dunebugger_system_info import SystemInfoModel


class MessageHandler:
    def __init__(self, heart_beat_every_secs, heart_beat_loop_duration_secs):
        self.websocket_client = None
        self.messaging_queue_handler = None
        self.component_updater = None  # Will be set by class_factory
        self.heart_beat_every_secs = heart_beat_every_secs
        self.heart_beat_loop_duration_secs = heart_beat_loop_duration_secs
        self.countdown_timer = 0
        self.alive_message = {
            "body": "I am alive",
            "subject": "heartbeat",
            "source": "controller",
            "destination": "broadcast",
        }
        self.heartbeat_event = threading.Event()
        self.countdown_event = threading.Event()
        self.system_info_model = SystemInfoModel()
        
        # Core heartbeat monitoring
        self.component_heartbeat_message = {
            "body": "are you there?",
            "subject": "heartbeat",
            "source": "controller"
        }
        self._heartbeat_task = None
        
        threading.Thread(target=self._send_heartbeat, daemon=True).start()
        threading.Thread(target=self._countdown, daemon=True).start()

    async def process_websocket_message(self, websocket_message):
        try:
            original_subject = websocket_message["subject"]
            source = websocket_message.get("source", "unknown")

            if source == "controller":
                logger.debug("Ignoring message from self.")
                return
            
            # Split subject into recipient and subject if it contains a dot
            recipient = None
            subject = original_subject
            
            if "." in original_subject:
                parts = original_subject.split(".", 1)  # Split on first dot only
                recipient = parts[0]
                subject = parts[1]
                logger.debug(f"Split subject '{original_subject}' into recipient='{recipient}' and subject='{subject}'")
                # Create a modified message with the new subject
                modified_message = websocket_message.copy()
                modified_message["subject"] = subject

            if recipient in ["core", "scheduler"]:
                await self.messaging_queue_handler.mqueue_sender.send(modified_message, recipient)
                logger.debug(f"Message routed to recipient '{recipient}' with subject '{subject}'")
            elif recipient in ["controller","updater"]:
                # Handle messages without recipients using existing logic
                if subject in ["heartbeat"]: #controller heartbeat
                    self.websocket_client.send_message(self.alive_message)
                    self.handle_heartbeat()
                elif subject in ["system_info"]: 
                    self.send_system_info()
                elif subject in ["ntp_status"]:
                    self.send_ntp_status()
                elif subject in ["check_updates"]:
                    await self.handle_check_updates(websocket_message)
                elif subject in ["update"]:
                    await self.handle_perform_update(websocket_message)
                else:
                    logger.debug(f"Unknown subject for controller recipient: {subject}. Ignoring message.")
            else:
                logger.debug(f"No recipient specified or unkown recipient, ignoring recipient routing for subject '{original_subject}'")


        except KeyError as key_error:
            logger.error(f"KeyError: {key_error}. Message: {websocket_message}")
        except Exception as e:
            logger.error(f"Error processing message: {e}. Message: {websocket_message}")

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
            time.sleep(self.heart_beat_every_secs)

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
        self.countdown_timer = self.heart_beat_loop_duration_secs
        self.heartbeat_event.set()  # Activate heartbeat loop
        self.countdown_event.set()  # Activate countdown loop

    def send_log(self, log_message):
        data = {"body": log_message, "subject": "log", "source": "controller"}
        self.websocket_client.send_message(data)
    
    def send_system_info(self):
        """Send system information on startup or on demand"""
        try:
            system_info = self.system_info_model.get_system_info()
            self.dispatch_message(system_info, "system_info")
            logger.info("System information sent successfully")
        except Exception as e:
            logger.error(f"Failed to send system information: {e}")
    
    def send_ntp_status(self):
        """Send NTP status on demand"""
        try:
            ntp_status = {
                "ntp_available": bool(self.system_info_model.is_ntp_available())
            }
            self.dispatch_message(ntp_status, "ntp_status")
            logger.info("NTP status sent successfully")
        except Exception as e:
            logger.error(f"Failed to send NTP status: {e}")
    
    async def handle_check_updates(self, websocket_message):
        """Handle check_updates request from WebSocket"""
        try:
            if not self.component_updater:
                logger.error("Component updater not initialized")
                self.dispatch_message(
                    {"error": "Component updater not available"},
                    "update_check_result"
                )
                return
            
            # Force check for updates
            force = websocket_message.get('body', {}).get('force', True)
            logger.info(f"Manual update check requested (force={force})")
            
            results = await self.component_updater.check_updates(force=force)
            
            # Format response
            response = {
                "components": {
                    key: {
                        "current": comp.current_version,
                        "latest": comp.latest_version,
                        "update_available": comp.update_available,
                        "release_notes": comp.release_notes,
                        "last_checked": comp.last_checked.isoformat() if comp.last_checked else None
                    }
                    for key, comp in results.items()
                }
            }
            
            self.dispatch_message(response, "update_check_result")
            logger.info("Update check completed and sent")
            
        except Exception as e:
            logger.error(f"Failed to handle check_updates: {e}")
            self.dispatch_message(
                {"error": str(e)},
                "update_check_result"
            )
    
    async def handle_perform_update(self, websocket_message):
        """Handle perform_update request from WebSocket"""
        try:
            if not self.component_updater:
                logger.error("Component updater not initialized")
                self.dispatch_message(
                    {"error": "Component updater not available"},
                    "update_result"
                )
                return
            
            component = websocket_message.get('body', None)
            
            # Remove prefix "dunebugger-" if present
            if component and component.startswith("dunebugger-"):
                component = component[len("dunebugger-"):]

            if not component:
                raise ValueError("No component specified for update")
            
            logger.info(f"Update requested for component: {component})")
            
            # Perform the update. Result should contain the component's name
            response = await self.component_updater.update_component(component)
            
            # response pattern: 
            # response = {
            #     "success": True|False,
            #     "message": result,
            #     "level": "info"|"error"|"warning",
            # }
            
            self.dispatch_message(response, "log")
            logger.info(f"Update result sent: {response}")
            
        except Exception as e:
            logger.error(f"Failed to handle perform_update: {e}")
            self.dispatch_message(
                message_body={"message": f"Error while updating component {component}: {str(e)}", "success": False, "level": "error"},
                subject="log"
            )

    async def start_components_heartbeat(self):
        """Start the async heartbeat task"""
        if self._heartbeat_task is None:
            self._heartbeat_task = asyncio.create_task(self._send_components_heartbeat_loop())
            logger.info("Components heartbeat monitoring started")
    
    async def _send_components_heartbeat_loop(self):
        """Send heartbeats to local components every 30 seconds"""
        while True:
            try:
                await asyncio.sleep(30)  # Wait 30 seconds between heartbeats
                
                if self.messaging_queue_handler and self.messaging_queue_handler.mqueue_sender:
                    await self.messaging_queue_handler.mqueue_sender.send(
                        self.component_heartbeat_message, 
                        "core"
                    )
                    logger.debug("Core heartbeat sent")
                    await self.messaging_queue_handler.mqueue_sender.send(
                        self.component_heartbeat_message, 
                        "scheduler"
                    )
                    logger.debug("Scheduler heartbeat sent")
                else:
                    logger.debug("Messaging queue handler not available for heartbeat")
            except asyncio.CancelledError:
                logger.info("Components heartbeat monitoring stopped")
                break
            except Exception as e:
                logger.error(f"Error sending components heartbeat: {e}")
                # Continue the loop even if there's an error
