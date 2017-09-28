from apscheduler.schedulers.blocking import BlockingScheduler
from flask import Flask, request, Response, jsonify
from slackclient import SlackClient
import os
app = Flask(__name__)
sched = BackgroundScheduler()
slack_client = SlackClient(os.environ['SLACKID'])

@sched.scheduled_job('cron', day_of_week='mon-fri', hour=15, minute=12)
def scheduled_job():
    slack_client.api_call(
      "chat.postMessage",
      channel="#christinastestchannel",
      text="Please reply here with your standup status if you won't be in the office today!"
    )
    print("Standup message sent")

@app.route('/run')
def run_bot():
    sched.start()
    print("test")

@app.route('/')
def homepage():
    return """
    KarmaBot
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0')


sched.start()
print("test 2")
