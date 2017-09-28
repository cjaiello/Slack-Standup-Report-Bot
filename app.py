from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, Response, jsonify
from slackclient import SlackClient
import os
from time import gmtime, strftime

app = Flask(__name__)
sched = BackgroundScheduler()
slack_client = SlackClient(os.environ['SLACKID'])

@sched.scheduled_job('cron', day_of_week='mon-fri', hour=15, minute=50)
def scheduled_job():
    slack_client.api_call(
      "chat.postMessage",
      channel="#christinastestchannel",
      text="@channel Please reply here with your standup status if you won't be in the office today!",
      username="Standup Bot"
    )
    print("Standup alert message sent on " + strftime("%Y-%m-%d %H:%M:%S", gmtime()))

if __name__ == '__main__':
    app.run(host='0.0.0.0')

sched.start()
print("Standup bot was scheduled on " + strftime("%Y-%m-%d %H:%M:%S", gmtime()))
