# Standup Bot by Christina Aiello, 2017-2020
import re
from logger import Logger
import random

# For logging purposes
def format_minutes_to_have_zero(minutes):
    if minutes == None:
        return "00"
    else:
        if(int(minutes) < 10):
            return "0" + str(minutes)
        else:
            return str(minutes)


# Generate a random 6-digit code
def generate_code():
  code = ""
  for i in range (1, 7):
    code += (str(random.randrange(10)))
  return code


# Scheduler doesn't like zeros at the start of numbers...
# @param time: string to remove starting zeros from
def remove_starting_zeros_from_time(time):
    return (re.search( r'0?(\d+)?', time, re.M|re.I)).group(1)


# Adds 12 if PM else keeps as original time. When we insert
# data from the form into the database, we convert from AM/PM
# to 24-hour time.
def calculate_am_or_pm(reminder_hour, am_or_pm):
    Logger.log("Hour is: " + str(reminder_hour) + " and am or pm is: " + am_or_pm, "INFO") # Issue 25: eventType: CalculateAmOrPm
    reminder_hour = int(reminder_hour)
    if (am_or_pm == "pm" and reminder_hour != 12):
        reminder_hour += 12
    elif (am_or_pm == "am" and reminder_hour == 12):
        reminder_hour = 0
    Logger.log("Hour now is: " + str(reminder_hour) + " and am or pm is: " + am_or_pm, "INFO") # Issue 25: eventType: CalculateAmOrPm
    return reminder_hour
