from os import path
import configparser
from dotenv import load_dotenv
from dunebuggger_logging import logger, get_logging_level_from_name, set_logger_level
from utils import is_raspberry_pi


class DunebuggerSettings:
    def __init__(self):
        load_dotenv()
        self.config = configparser.ConfigParser()
        # Set optionxform to lambda x: x to preserve case
        self.config.optionxform = lambda x: x
        self.terminal_interpreter_command_handlers = {}
        self.load_configuration()
        self.override_configuration()
        set_logger_level("dunebuggerLog", self.dunebuggerLogLevel)

    def show_configuration(self):
        print("Current Configuration:")
        for attr_name in dir(self):
            if not attr_name.startswith("__") and not callable(getattr(self, attr_name)):
                print(f"{attr_name}: {getattr(self, attr_name)}")

    def load_configuration(self):
        try:
            dunebuggerConfig = path.join(path.dirname(path.abspath(__file__)), "config/dunebugger.conf")
            self.config.read(dunebuggerConfig)

            for section in ["General", "Auth", "Websocket", "MessageQueue", "Log"]:
                for option in self.config.options(section):
                    value = self.config.get(section, option)
                    setattr(self, option, self.validate_option(section, option, value))
                    logger.debug(f"{option}: {value}")

            self.ON_RASPBERRY_PI = is_raspberry_pi()
            logger.debug(f"ON_RASPBERRY_PI: {self.ON_RASPBERRY_PI}")
            logger.info("Configuration loaded successfully")
        except configparser.Error as e:
            logger.error(f"Error reading {dunebuggerConfig} configuration: {e}")

    def validate_option(self, section, option, value):
        # Validation for specific options
        try:
            if section == "General":
                if option in [
                    "pipePath",
                ]:
                    return str(value)
            elif section == "Auth":
                if option in ["authURL"]:
                    return str(value)
            elif section == "Websocket":
                if option in ["websocketEnabled", "broadcastInitialState"]:
                    return self.config.getboolean(section, option)
                elif option in ["stateCheckIntervalSecs", "cyclePlayingResolutionSecs"]:
                    return int(value)
            elif section == "MessageQueue":
                if option in ["mQueueMode", "mQueueAddress", "mQueueTopic"]:
                    return str(value)
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

    def override_configuration(self):
        if not self.ON_RASPBERRY_PI:
            self.vlcdevice = ""


settings = DunebuggerSettings()
