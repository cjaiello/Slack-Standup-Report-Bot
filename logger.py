from time import localtime, strftime

# Used for logging when actions happen
# @return string with logging time
def create_logging_label():
    return "[" + strftime("%Y-%m-%d %H:%M:%S", localtime()) + "]"

def log(message_to_log, log_level):
  print(create_logging_label() + "[" + log_level +"] " + message_to_log)