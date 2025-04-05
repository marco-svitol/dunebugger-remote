import logging
import logging.config
from os import path

logConfig = path.join(path.dirname(path.abspath(__file__)), "config/dunebuggerlogging.conf")
logging.config.fileConfig(logConfig)  # load logging config file
logger = logging.getLogger("dunebuggerLog")

COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "BLUE": "\033[94m",
    "MAGENTA": "\033[95m",
    "CYAN": "\033[96m",
    "RESET": "\033[0m",
}


class CustomFormatter(logging.Formatter):
    def format(self, record):
        log_fmt = self._style._fmt
        if record.levelno == logging.ERROR:
            log_fmt = COLORS["RED"] + log_fmt + COLORS["RESET"]
        elif record.levelno == logging.WARNING:
            log_fmt = COLORS["YELLOW"] + log_fmt + COLORS["RESET"]
        elif record.levelno == logging.DEBUG:
            log_fmt = COLORS["BLUE"] + log_fmt + COLORS["RESET"]
        formatter = logging.Formatter(log_fmt, self.datefmt)
        return formatter.format(record)


def get_logging_level_from_name(level_str):
    # Convert the string level to a logging level
    level = getattr(logging, level_str.upper(), None)
    if not isinstance(level, int):
        return ""
    else:
        return level


def set_logger_level(logger_name, level):
    try:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        print(f"Logger {logger_name} level set to {logging.getLevelName(level)}")
    except Exception as exc:
        print(f"Error while setting logger ${logger_name} level to {logging.getLevelName(level)}: ${str(exc)}")


# Get the console handler and set the custom formatter
console_handler = logger.handlers[0]
console_handler.setFormatter(CustomFormatter("%(levelname)s - %(asctime)s : %(message)s", "%d/%m/%Y %H:%M:%S"))
