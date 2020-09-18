# Standup Bot by Christina Aiello, 2017
import re

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


# Adds 12 if PM else keeps as original time. When we insert
# data from the form into the database, we convert from AM/PM
# to 24-hour time.
def calculate_am_or_pm(reminder_hour, am_or_pm):
    if (am_or_pm == "pm"):
        reminder_hour  = int(reminder_hour) + 12
    return reminder_hour
