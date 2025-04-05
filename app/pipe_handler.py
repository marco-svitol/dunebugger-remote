import os
import threading
from dunebugger_settings import settings
import time


class PipeListener:
    def __init__(self):
        self.terminal_interpreter = None
        self.pipe_path = settings.pipePath
        if not os.path.exists(self.pipe_path):
            os.mkfifo(self.pipe_path)

    def pipe_input_thread(self):
        with open(self.pipe_path) as pipe:
            while True:
                command = pipe.readline().strip()
                if command:
                    self.terminal_interpreter.process_terminal_input(command)
                time.sleep(0.1)  # Sleep for 100 milliseconds to reduce CPU usage

    def pipe_listen(self):
        # Start a separate thread for reading from the named pipe
        pipe_thread = threading.Thread(target=self.pipe_input_thread, daemon=True)
        pipe_thread.start()
        # remove comment belowe when ready to make a real server
        # while not terminal_interpreter.stop_terminal_event.is_set():
        #    time.sleep(0.1)

    def pipe_send(self, stream):
        with open(self.pipe_path, "w") as pipe:
            pipe.write(stream + "\n")
