import os
from dunebugger_auth import AuthClient
from dunebugger_websocket import WebPubSubListener
from message_handler import MessageHandler
from pipe_handler import PipeListener
from dunebugger_settings import settings


auth_client = AuthClient(
    client_id=os.getenv("AUTH0_CLIENT_ID"),
    client_secret=os.getenv("AUTH0_CLIENT_SECRET"),
    username=os.getenv("AUTH0_USERNAME"),
    password=os.getenv("AUTH0_PASSWORD"),
)

websocket_client = WebPubSubListener()
message_handler = MessageHandler()
pipe_listener = PipeListener()


message_handler.websocket_client = websocket_client
message_handler.pipe_listener = pipe_listener
websocket_client.auth_client = auth_client
websocket_client.message_handler = message_handler
