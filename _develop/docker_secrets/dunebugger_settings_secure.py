import os
from pathlib import Path
from os import path
import configparser
from dotenv import load_dotenv
from dunebugger_logging import logger, get_logging_level_from_name, set_logger_level

class SecureSettingsManager:
    """
    Secure settings manager that handles environment variables and Docker secrets safely.
    Priority order: Docker Secrets > Environment Variables > Config File > Default Values
    """
    
    def __init__(self):
        load_dotenv()
        self.config = configparser.ConfigParser()
        # Set optionxform to lambda x: x to preserve case
        self.config.optionxform = lambda x: x
        self.dunebugger_config = path.join(path.dirname(path.abspath(__file__)), "config/dunebugger.conf")
        self.secrets_path = "/run/secrets"  # Default Docker secrets mount point
        self.load_configuration()

    def _read_docker_secret(self, secret_name):
        """
        Safely read a Docker secret from /run/secrets/
        """
        try:
            secret_file = Path(self.secrets_path) / secret_name
            if secret_file.exists():
                with open(secret_file, 'r') as f:
                    secret_value = f.read().strip()
                logger.debug(f"Loaded secret: {secret_name}")
                return secret_value
        except Exception as e:
            logger.warning(f"Could not read Docker secret '{secret_name}': {e}")
        return None

    def _get_secure_value(self, config_section, config_key, env_var_name=None, secret_name=None, default_value=None):
        """
        Get configuration value with security priority:
        1. Docker secret (highest priority)
        2. Environment variable
        3. Config file value
        4. Default value (lowest priority)
        """
        # Try Docker secret first
        if secret_name:
            secret_value = self._read_docker_secret(secret_name)
            if secret_value:
                return secret_value

        # Try environment variable
        if env_var_name:
            env_value = os.getenv(env_var_name)
            if env_value:
                logger.debug(f"Using environment variable: {env_var_name}")
                return env_value

        # Try config file
        try:
            if self.config.has_option(config_section, config_key):
                config_value = self.config.get(config_section, config_key)
                logger.debug(f"Using config file value for: {config_key}")
                return config_value
        except configparser.Error:
            pass

        # Return default value
        if default_value is not None:
            logger.debug(f"Using default value for: {config_key}")
            return default_value

        raise ValueError(f"No value found for {config_section}.{config_key}")

    def load_configuration(self, dunebugger_config=None):
        if dunebugger_config is None:
            dunebugger_config = self.dunebugger_config

        try:
            # Load config file first (as base)
            self.config.read(dunebugger_config)
            
            # Load secure values with priority order
            self._load_secure_settings()
            
            # Set logging level
            set_logger_level("dunebuggerLog", self.dunebuggerLogLevel)
            logger.info("Secure configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise

    def _load_secure_settings(self):
        """Load all settings using secure value resolution"""
        
        # General settings
        self.general_setting = self._get_secure_value(
            "General", "general_setting",
            env_var_name="GENERAL_SETTING",
            default_value="dummy"
        )

        # Authentication settings (sensitive)
        self.authURL = self._get_secure_value(
            "Auth", "authURL",
            env_var_name="AUTH0_DOMAIN",
            secret_name="auth0_domain",
            default_value="dunebugger.eu.auth0.com"
        )
        
        # If you have client ID and secret, add them here
        self.auth0_client_id = self._get_secure_value(
            "Auth", "clientID",
            env_var_name="AUTH0_CLIENT_ID",
            secret_name="auth0_client_id"
        ) if os.getenv("AUTH0_CLIENT_ID") or self._read_docker_secret("auth0_client_id") else None
        
        self.auth0_client_secret = self._get_secure_value(
            "Auth", "clientSecret",
            env_var_name="AUTH0_CLIENT_SECRET",
            secret_name="auth0_client_secret"
        ) if os.getenv("AUTH0_CLIENT_SECRET") or self._read_docker_secret("auth0_client_secret") else None

        # Websocket settings
        self.websocketEnabled = self._get_bool_value("Websocket", "websocketEnabled", "WEBSOCKET_ENABLED", default_value=True)
        self.broadcastInitialState = self._get_bool_value("Websocket", "broadcastInitialState", "BROADCAST_INITIAL_STATE", default_value=True)
        self.stateCheckIntervalSecs = self._get_int_value("Websocket", "stateCheckIntervalSecs", "STATE_CHECK_INTERVAL_SECS", default_value=2)
        self.cyclePlayingResolutionSecs = self._get_int_value("Websocket", "cyclePlayingResolutionSecs", "CYCLE_PLAYING_RESOLUTION_SECS", default_value=10)
        self.heartBeatLoopDurationSecs = self._get_int_value("Websocket", "heartBeatLoopDurationSecs", "HEARTBEAT_LOOP_DURATION_SECS", default_value=300)
        self.heartBeatEverySecs = self._get_int_value("Websocket", "heartBeatEverySecs", "HEARTBEAT_EVERY_SECS", default_value=60)
        self.testDomain = self._get_secure_value("Websocket", "testDomain", "TEST_DOMAIN", default_value="smart.dunebugger.it")
        self.connectionIntervalSecs = self._get_int_value("Websocket", "connectionIntervalSecs", "CONNECTION_INTERVAL_SECS", default_value=60)
        self.connectionTimeoutSecs = self._get_int_value("Websocket", "connectionTimeoutSecs", "CONNECTION_TIMEOUT_SECS", default_value=2)

        # Message Queue settings
        self.mQueueServers = self._get_secure_value("MessageQueue", "mQueueServers", "MQUEUE_SERVERS", default_value="nats://nats-server:4222")
        self.mQueueClientID = self._get_secure_value("MessageQueue", "mQueueClientID", "MQUEUE_CLIENT_ID", default_value="remote")
        self.mQueueSubjectRoot = self._get_secure_value("MessageQueue", "mQueueSubjectRoot", "MQUEUE_SUBJECT_ROOT", default_value="dunebugger")
        self.mQueueStateCheckIntervalSecs = self._get_int_value("MessageQueue", "mQueueStateCheckIntervalSecs", "MQUEUE_STATE_CHECK_INTERVAL_SECS", default_value=30)
        self.mQueueCyclePlayingResolutionSecs = self._get_int_value("MessageQueue", "mQueueCyclePlayingResolutionSecs", "MQUEUE_CYCLE_PLAYING_RESOLUTION_SECS", default_value=10)

        # Logging settings
        log_level_str = self._get_secure_value("Log", "dunebuggerLogLevel", "LOG_LEVEL", default_value="DEBUG")
        self.dunebuggerLogLevel = get_logging_level_from_name(log_level_str) or get_logging_level_from_name("INFO")

        # Database settings (if you have any)
        self.db_password = self._get_secure_value(
            "Database", "password",
            env_var_name="DB_PASSWORD",
            secret_name="db_password"
        ) if os.getenv("DB_PASSWORD") or self._read_docker_secret("db_password") else None

        # API Keys (if you have any)
        self.api_key = self._get_secure_value(
            "API", "key",
            env_var_name="API_KEY",
            secret_name="api_key"
        ) if os.getenv("API_KEY") or self._read_docker_secret("api_key") else None

    def _get_bool_value(self, section, key, env_var_name, default_value=False):
        """Get boolean value from secure sources"""
        value = self._get_secure_value(section, key, env_var_name, default_value=str(default_value))
        return str(value).lower() in ('true', '1', 'yes', 'on')

    def _get_int_value(self, section, key, env_var_name, default_value=0):
        """Get integer value from secure sources"""
        value = self._get_secure_value(section, key, env_var_name, default_value=str(default_value))
        try:
            return int(value)
        except ValueError:
            logger.warning(f"Could not convert {key} value '{value}' to integer, using default: {default_value}")
            return default_value

    def validate_option(self, section, option, value):
        """Legacy compatibility method"""
        return value

# Create the settings instance
settings = SecureSettingsManager()