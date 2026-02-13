from dunebugger_settings import settings
from dunebugger_auth import AuthClient
from dunebugger_websocket import WebPubSubListener
from websocket_message_handler import MessageHandler
from mqueue import NATSComm
from mqueue_handler import MessagingQueueHandler
from internet_monitor import InternetConnectionMonitor
from ntp_monitor import NTPMonitor
from dunebugger_updater import ComponentUpdater

internet_monitor = InternetConnectionMonitor(test_domain=settings.testDomain, check_interval=settings.connectionIntervalSecs, timeout=settings.connectionTimeoutSecs)

# Initialize component updater
component_updater = ComponentUpdater()

auth_client = AuthClient(
    client_id=settings.clientID,
    client_secret=settings.clientSecret,
    username=settings.username,
    password=settings.password,
)

websocket_message_handler = MessageHandler(settings.heartBeatEverySecs, settings.heartBeatLoopDurationSecs)
websocket_client = WebPubSubListener(internet_monitor, auth_client, websocket_message_handler)

mqueue_handler = MessagingQueueHandler(websocket_message_handler)
mqueue = NATSComm(
    nat_servers=settings.mQueueServers,
    client_id=settings.mQueueClientID,
    subject_root=settings.mQueueSubjectRoot,
    mqueue_handler=mqueue_handler,
)

# Initialize NTP monitor with system info model
ntp_monitor = NTPMonitor(websocket_message_handler.system_info_model)

mqueue_handler.mqueue_sender = mqueue
mqueue_handler.component_updater = component_updater
websocket_message_handler.websocket_client = websocket_client
websocket_message_handler.messaging_queue_handler = mqueue_handler

# Wire up NTP monitor dependencies
ntp_monitor.websocket_message_handler = websocket_message_handler
ntp_monitor.set_messaging_queue_handler(mqueue_handler)
mqueue_handler.ntp_monitor = ntp_monitor

# Wire up component updater
websocket_message_handler.component_updater = component_updater
websocket_message_handler.system_info_model.component_updater = component_updater
component_updater.set_dispatch_callback(websocket_message_handler.dispatch_message)

# Start internet monitoring if WebSocket is enabled
if settings.websocketEnabled is True:
    internet_monitor.start_monitoring()
