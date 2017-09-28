from apscheduler.schedulers.blocking import BlockingScheduler
from flask import Flask, request, Response, jsonify
from slackclient import SlackClient
import os
app = Flask(__name__)
sched = BlockingScheduler()

slack_token = os.environ["SLACKID"]
slack_client = SlackClient(slack_token)

@sched.scheduled_job('cron', day_of_week='mon-fri', hour=14, minute=1)
def scheduled_job():
    slack_client.api_call(
      "chat.postMessage",
      channel="#christinastestchannel",
      text="Please reply here with your standup status if you won't be in the office today!"
    )
    print("Standup message sent")

if __name__ == '__main__':
    app.run(host='0.0.0.0')
    sched.start()
