# Standup Bot by Christina Aiello, 2017. cjaiello@wpi.edu

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, Response, jsonify, render_template
from slackclient import SlackClient
import os
from time import localtime, strftime
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField
import psycopg2
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
sched = BackgroundScheduler()
slack_client = SlackClient(os.environ['SLACK_BOT_TOKEN'])


# Create our database model
class Channel(db.Model):
    __tablename__ = "channel"
    id = db.Column(db.Integer, primary_key=True)
    channel_name = db.Column(db.String(120), unique=True)
    standup_time = db.Column(db.Integer)

    def __init__(self, channel_name, standup_time):
        self.channel_name = channel_name
        self.standup_time = standup_time

    def __repr__(self):
        return '<Channel %r>' % self.channel_name


# Our form model
class ReusableForm(Form):
    submitted_channel_name = TextField('Channel Name:', validators=[validators.required()])
    standup_time = TextField('Standup Time:', validators=[validators.required()])


@app.route("/", methods=['GET', 'POST'])
def homepage():
    form = ReusableForm(request.form)

    if request.method == 'POST':
        # Get whatever name they gave us for a channel
        submitted_channel_name = request.form['submitted_channel_name']
        standup_time = request.form['standup_time']
        # If the form field was valid...
        if form.validate():
            # Look for channel in database
            if not db.session.query(Channel).filter(Channel.channel_name == submitted_channel_name).count():
                # Channel isn't in database. Create our channel object
                channel = Channel(submitted_channel_name, standup_time)
                # Add it to the database
                db.session.add(channel)
                db.session.commit()
                # Adding this additional job to the queue
                sched.add_job(standup_call, 'cron', [channel.channel_name], day_of_week='mon-fri', hour=standup_time, id=channel.channel_name)
                print(strftime("%Y-%m-%d %H:%M:%S", localtime()) + ": Set " + submitted_channel_name + "'s standup time to " + str(standup_time))
            else:
                # If channel is in database, update channel's standup time
                channel = Channel.query.filter_by(channel_name = submitted_channel_name).first()
                channel.standup_time = standup_time
                db.session.commit()
                # Updating this job's timing
                sched.reschedule_job(channel.channel_name, trigger='cron', day_of_week='mon-fri', hour=standup_time)
                print(strftime("%Y-%m-%d %H:%M:%S", localtime()) + ": Updated " + submitted_channel_name + "'s standup time to " + str(standup_time))
        else:
            print(strftime("%Y-%m-%d %H:%M:%S", localtime()) + ": Could not update " + submitted_channel_name + "'s standup time to " + str(standup_time))

    return render_template('homepage.html', form=form)


# Setting the standup schedules for already-existing jobs
def set_schedules():
    # Get all rows from our table
    channels_with_scheduled_standups = Channel.query.all()
    # Loop through our results
    for channel in channels_with_scheduled_standups:
        # Add a job for each row in the table
        sched.add_job(standup_call, 'cron', [channel.channel_name], day_of_week='mon-fri', hour=channel.standup_time, id=channel.channel_name)
        print(strftime("%Y-%m-%d %H:%M:%S", localtime()) + ": Channel name and time that we set the schedule for: " + channel.channel_name + " at " + str(channel.standup_time))


# Function that triggers the standup call
def standup_call(channel_name):
    result = slack_client.api_call(
      "chat.postMessage",
      channel=str(channel_name),
      text="<!channel> Please reply here with your standup status if you won't be in the office today!",
      username="Standup Bot",
      icon_emoji=":memo:"
    )
    print(strftime("%Y-%m-%d %H:%M:%S", localtime()) + ": Standup alert message sent to " + channel_name)
    print(strftime("%Y-%m-%d %H:%M:%S", localtime()) + ": Result of sending standup message to " + channel_name + " was " + result)


if __name__ == '__main__':
    app.run(host='0.0.0.0')

# Setting the scheduling
set_schedules()
# Running the scheduling
sched.start()
print(strftime("%Y-%m-%d %H:%M:%S", localtime()) + ": Standup bot was started up and scheduled.")
