from os import path
import configparser
from dotenv import load_dotenv
from dunebugger_logging import logger, get_logging_level_from_name, set_logger_level

class DunebuggerSettings:
    def __init__(self):
        load_dotenv()
        self.config = configparser.ConfigParser()
        # Set optionxform to lambda x: x to preserve case
        self.config.optionxform = lambda x: x
        self.dunebugger_config = path.join(path.dirname(path.abspath(__file__)), "config/dunebugger.conf")
        self.load_configuration(self.dunebugger_config)
        set_logger_level("dunebuggerLog", self.dunebuggerLogLevel)

    def load_configuration(self, dunebugger_config=None):
        if dunebugger_config is None:
            dunebugger_config = self.dunebugger_config

        try:
            self.config.read(dunebugger_config)
            for section in ["General", "Auth", "Websocket", "MessageQueue", "Log"]:
                for option in self.config.options(section):
                    value = self.config.get(section, option)
                    setattr(self, option, self.validate_option(section, option, value))
                    logger.debug(f"{option}: {value}")

            logger.info("Configuration loaded successfully")
        except configparser.Error as e:
            logger.error(f"Error reading {dunebugger_config} configuration: {e}")

    def validate_option(self, section, option, value):
        # Validation for specific options
        try:
            if section == "General":
                if option in [
                    "general_setting"
                ]:
                    return str(value)
            elif section == "Auth":
                if option in ["authURL"]:
                    return str(value)
            elif section == "Websocket":
                if option in ["websocketEnabled", "broadcastInitialState"]:
                    return self.config.getboolean(section, option)
                elif option in ["stateCheckIntervalSecs", "cyclePlayingResolutionSecs", "heartBeatLoopDurationSecs", "heartBeatEverySecs", "connectionIntervalSecs", "connectionTimeoutSecs"]:
                    return int(value)
                elif option in ["testDomain"]:
                    return str(value)
            elif section == "MessageQueue":
                if option in ["mQueueServers", "mQueueClientID", "mQueueSubjectRoot"]:
                    return str(value)
                elif option in ["mQueueStateCheckIntervalSecs", "mQueueCyclePlayingResolutionSecs"]:
                    return int(value)
            elif section == "Log":
                logLevel = get_logging_level_from_name(value)
                if logLevel == "":
                    return get_logging_level_from_name("INFO")
                else:
                    return logLevel

        except (configparser.NoOptionError, ValueError) as e:
            raise ValueError(f"Invalid configuration: Section={section}, Option={option}, Value={value}. Error: {e}")

        # If no specific validation is required, return the original value
        return value

settings = DunebuggerSettings()
