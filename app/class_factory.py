import os
from dunebugger_settings import settings
from dunebugger_auth import AuthClient
from dunebugger_websocket import WebPubSubListener
from websocket_message_handler import MessageHandler
from mqueue import ZeroMQComm
from mqueue_handler import MessagingQueueHandler

auth_client = AuthClient(
    client_id=os.getenv("AUTH0_CLIENT_ID"),
    client_secret=os.getenv("AUTH0_CLIENT_SECRET"),
    username=os.getenv("AUTH0_USERNAME"),
    password=os.getenv("AUTH0_PASSWORD"),
)

websocket_message_handler = MessageHandler()
websocket_client = WebPubSubListener(auth_client, websocket_message_handler)

mqueue_handler = MessagingQueueHandler(websocket_message_handler)
mqueue_listener = ZeroMQComm(
    mode="REP",
    address=settings.mQueueListenerAddress,
    mqueue_handler=mqueue_handler,
)
mqueue_sender = ZeroMQComm(
    mode="REQ",
    address=settings.mQueueSenderAddress,
    mqueue_handler=mqueue_handler,
)

mqueue_handler.mqueue_sender = mqueue_sender
websocket_message_handler.websocket_client = websocket_client
websocket_message_handler.messaging_queue_handler = mqueue_handler
