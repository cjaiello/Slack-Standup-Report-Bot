from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, Response, jsonify, render_template
from slackclient import SlackClient
import os
from time import localtime, strftime
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField

app = Flask(__name__)
sched = BackgroundScheduler()
slack_client = SlackClient(os.environ['SLACKID'])

standup_dictionary = {'christinastestchannel' : 4}

@sched.scheduled_job('cron', day_of_week='mon-fri', hour=9)
def scheduled_job():
    slack_client.api_call(
      "chat.postMessage",
      channel="#christinastestchannel",
      text="<!channel> Please reply here with your standup status if you won't be in the office today!",
      username="Standup Bot",
      icon_emoji=":memo:"
    )
    print("Standup alert message sent on " + strftime("%Y-%m-%d %H:%M:%S", localtime()))

class ReusableForm(Form):
    squad_name = TextField('Squad Name:', validators=[validators.required()])
    standup_time = TextField('Standup Time:', validators=[validators.required()])


@app.route("/", methods=['GET', 'POST'])
def homepage():
    form = ReusableForm(request.form)

    print form.errors
    if request.method == 'POST':
        squad_name = request.form['squad_name']

        if form.validate():
            standup_dictionary[squad_name] = request.form['standup_time']
            print(standup_dictionary[squad_name])

    return render_template('homepage.html', form=form)

if __name__ == '__main__':
    app.run(host='0.0.0.0')

sched.start()
print("Standup bot was scheduled on " + strftime("%Y-%m-%d %H:%M:%S", localtime()))
