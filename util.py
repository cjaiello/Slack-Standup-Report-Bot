# Standup Bot by Christina Aiello, 2017
from time import localtime, strftime
import re

# Used for logging when actions happen
# @return string with logging time
def create_logging_label():
    return strftime("%Y-%m-%d %H:%M:%S", localtime()) + "| "


# For logging purposes
def format_minutes_to_have_zero(minutes):
    if minutes == None:
        return "00"
    else:
        if(int(minutes) < 10):
            return "0" + str(minutes)
        else:
            return str(minutes)


# Scheduler doesn't like zeros at the start of numbers...
# @param time: string to remove starting zeros from
def remove_starting_zeros_from_time(time):
    return (re.search( r'0?(\d+)?', time, re.M|re.I)).group(1)
