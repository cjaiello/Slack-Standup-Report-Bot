from apscheduler.schedulers.blocking import BlockingScheduler
from flask import Flask, request, Response, jsonify
from slackclient import SlackClient
import os
app = Flask(__name__)
sched = BlockingScheduler()
slack_client = SlackClient(os.environ['SLACKID'])

@sched.scheduled_job('cron', day_of_week='mon-fri', hour=14, minute=12)
def scheduled_job():
    slack_client.api_call(
      "chat.postMessage",
      channel="#christinastestchannel",
      text="Please reply here with your standup status if you won't be in the office today!"
    )
    print("Standup message sent")

@app.route('/')
def homepage():
    return """
    KarmaBot
    """

if __name__ == '__main__':
    print("Is this running?")
    app.run(host='0.0.0.0')
    slack_client.api_call(
      "chat.postMessage",
      channel="#christinastestchannel",
      text="Please reply here with your standup status if you won't be in the office today!"
    )
    sched.start()
