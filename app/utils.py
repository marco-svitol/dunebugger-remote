from dunebuggerlogging import logger
import os


def ArduinoSend(command):
    global Arduino
    ccommand = command.replace("\n", "")
    if Arduino is not False:
        Arduino.write(bytes(command, "UTF-8"))
        logger.debug("Sending command " + ccommand + " to Arduino")
    else:
        ccommand = command.replace("\n", "")
        logger.warning("ignoring command " + ccommand + " to Arduino")


def is_raspberry_pi():
    try:
        with open("/proc/device-tree/model") as model_file:
            model = model_file.read()
            if "Raspberry Pi" in model:
                return True
            else:
                return False
    except Exception:
        return False


def validate_path(path):
    if os.path.exists(path):
        return True
    else:
        return False
