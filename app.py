from apscheduler.schedulers.blocking import BlockingScheduler
from flask import Flask, request, Response, jsonify
from slackclient import SlackClient
import os

sched = BlockingScheduler()

slack_token = os.environ["SLACKID"]
sc = SlackClient(slack_token)

@sched.scheduled_job('cron', day_of_week='mon-fri', hour=13, minute=55)
def scheduled_job():
    sc.api_call(
      "chat.postMessage",
      channel="#christinastestchannel",
      text="Please reply here with your standup status if you won't be in the office today!"
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0')
    sched.start()
