from apscheduler.schedulers.background import BackgroundScheduler
from slackclient import SlackClient
import os
from time import gmtime, strftime

sched = BackgroundScheduler()
slack_client = SlackClient(os.environ['SLACKID'])

@sched.scheduled_job('cron', day_of_week='mon-fri', hour=15, minute=39)
def scheduled_job():
    slack_client.api_call(
      "chat.postMessage",
      channel="#christinastestchannel",
      text="Please reply here with your standup status if you won't be in the office today!",
      username="Standup Bot"
    )
    print("Standup alert message sent on " + strftime("%Y-%m-%d %H:%M:%S", gmtime()))

sched.start()
print("Standup bot was scheduled on " + strftime("%Y-%m-%d %H:%M:%S", gmtime()))
