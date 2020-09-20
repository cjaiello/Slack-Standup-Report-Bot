# Standup Bot by Christina Aiello, 2017-2020
from time import localtime, strftime

class Logger:
    info = "INFO"
    error = "ERROR"

    # Used for logging when actions happen
    # @return string with logging info
    @staticmethod
    def log(message_to_log, log_level):
        print("[" + strftime("%Y-%m-%d %H:%M:%S", localtime()) + "]" + "[" + log_level +"] " + message_to_log)