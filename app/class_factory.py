import os
from dunebugger_settings import settings
from dunebugger_auth import AuthClient
from dunebugger_websocket import WebPubSubListener
from websocket_message_handler import MessageHandler
from mqueue import NATSComm
from mqueue_handler import MessagingQueueHandler

auth_client = AuthClient(
    client_id=os.getenv("AUTH0_CLIENT_ID"),
    client_secret=os.getenv("AUTH0_CLIENT_SECRET"),
    username=os.getenv("AUTH0_USERNAME"),
    password=os.getenv("AUTH0_PASSWORD"),
)

websocket_message_handler = MessageHandler(settings.heartBeatEverySecs, settings.heartBeatLoopDurationSecs)
websocket_client = WebPubSubListener(auth_client, websocket_message_handler)

mqueue_handler = MessagingQueueHandler(websocket_message_handler)
mqueue = NATSComm(
    nat_servers=settings.mQueueServers,
    client_id=settings.mQueueClientID,
    subject_root=settings.mQueueSubjectRoot,
    mqueue_handler=mqueue_handler,
)

mqueue_handler.mqueue_sender = mqueue
websocket_message_handler.websocket_client = websocket_client
websocket_message_handler.messaging_queue_handler = mqueue_handler
