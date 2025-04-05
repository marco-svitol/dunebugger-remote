from dunebuggerlogging import logger
import http.client
import json

class AuthClient:
    def __init__(self, client_id, client_secret, username, password):
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.conn = http.client.HTTPSConnection("dunebugger.eu.auth0.com")
        self.headers = {
            "Content-Type": "application/json",
        }
        self.access_token = ""
        self.wss_url = ""
        self.user_id = ""
        self.name = ""
        self.user_picture = ""
        self.user_email = ""
        # try:
        #   self._update_user_info()
        # except Exception as e:
        #   logger.error(f"Error during initialization: {e}")

    def _update_user_info(self):
        try:
            self._get_auth_token()
            self._get_user_info()
            logger.info(f"User {self.name} updated")
        except Exception as e:
            logger.error(f"Error updating user info: {e}")

    def _get_auth_token(self):
        payload = json.dumps(
            {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "password",
                "username": self.username,
                "password": self.password,
                "scope": "openid profile email",
            }
        )
        try:
            self.conn.request("POST", "/oauth/token", payload, self.headers)
            res = self.conn.getresponse()
            data = res.read()
            # Parse the JSON response and save the access_token
            response_data = json.loads(data.decode("utf-8"))
            self.access_token = response_data.get("access_token")
            if not self.access_token:
                raise ValueError("Access token not found in response")
        except Exception as e:
            logger.error(f"Error getting auth token: {e}")
            raise

    def _get_user_info(self):
        payload = ""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
        }
        try:
            self.conn.request("GET", "/userinfo", payload, headers)
            res = self.conn.getresponse()
            data = res.read()
            # Parse the JSON response and return the wss_url
            user_info = json.loads(data.decode("utf-8"))
            self.wss_url = user_info.get("wss_url")
            self.user_id = user_info.get("sub")
            self.name = user_info.get("name")
            self.user_picture = user_info.get("picture")
            self.user_email = user_info.get("email")
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            raise
