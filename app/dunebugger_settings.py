import os
from dotenv import load_dotenv
from dunebugger_logging import logger, get_logging_level_from_name, set_logger_level

class DunebuggerSettings:
    def __init__(self):
        load_dotenv()
        self.options = {
            "Auth": ["authURL", "clientID", "clientSecret", "username", "password"],
            "Websocket": ["websocketEnabled", "broadcastInitialState", "heartBeatLoopDurationSecs", "heartBeatEverySecs", "testDomain", "connectionIntervalSecs", "connectionTimeoutSecs", "groupName"],
            "MessageQueue": ["mQueueServers", "mQueueClientID", "mQueueSubjectRoot"],
            "Log": ["dunebuggerLogLevel"],
            "NTP": ["ntpServers", "ntpCheckIntervalSecs", "ntpTimeout"],
            "Updater": ["githubAccount", "includePrerelease", "updateCheckIntervalHours", "dockerComposePath", "coreInstallPath", "backupPath"],
            "System": ["deviceID", "locationDescription"]
        }
        for section, options in self.options.items():
            for option in options:
                env_key = f"{section.upper()}_{option.upper()}"
                if option == "deviceID":
                    value = os.environ.get(env_key, "Environment Variable DEVICE_ID Not Set")
                elif option == "locationDescription":
                    value = os.environ.get(env_key, "Environment Variable LOCATION_DESCRIPTION Not Set")
                else:
                    value = os.environ.get(env_key)
                    if value is None:
                        logger.error(f"Environment variable {env_key} not set")
                        continue
                setattr(self, option, self.validate_option(section, option, value))
                logger.debug(f"{option}: {value}")
        set_logger_level("dunebuggerLog", self.dunebuggerLogLevel)

    def validate_option(self, section, option, value):
        # Validation for specific options
        try:
            if section == "Auth":
                if option in ["authURL", "clientID", "clientSecret", "username", "password"]:
                    return str(value)
            elif section == "Websocket":
                if option in ["websocketEnabled", "broadcastInitialState"]:
                    return value.lower() == 'true'
                elif option in ["heartBeatLoopDurationSecs", "heartBeatEverySecs", "connectionIntervalSecs", "connectionTimeoutSecs"]:
                    return int(value)
                elif option in ["testDomain", "groupName"]:
                    return str(value)
            elif section == "MessageQueue":
                if option in ["mQueueServers", "mQueueClientID", "mQueueSubjectRoot"]:
                    return str(value)
            elif section == "Log":
                logLevel = get_logging_level_from_name(value)
                if logLevel == "":
                    return get_logging_level_from_name("INFO")
                else:
                    return logLevel
            elif section == "NTP":
                if option in ["ntpServers"]:
                    # Return list of NTP servers
                    return [server.strip() for server in value.split(",")]
                elif option in ["ntpCheckIntervalSecs", "ntpTimeout"]:
                    return int(value)
            elif section == "Updater":
                if option in ["updateCheckIntervalHours"]:
                    return int(value)
                elif option in ["dockerComposePath", "coreInstallPath", "backupPath", "githubAccount"]:
                    return str(value)
                elif option in ["includePrerelease"]:
                    return value.lower() == 'true'
            elif section == "System":
                if option in ["deviceID", "locationDescription"]:
                    return str(value)

        except ValueError as e:
            raise ValueError(f"Invalid configuration: Section={section}, Option={option}, Value={value}. Error: {e}")

        # If no specific validation is required, return the original value
        return value

settings = DunebuggerSettings()
