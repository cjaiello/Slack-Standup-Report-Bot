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
                print("Set " + submitted_channel_name + "'s standup time to " + str(standup_time))
                # Adding this additional job to the queue
                sched.add_job(lambda: standup_call(channel.channel_name), 'cron', day_of_week='mon-fri', hour=0, minute=5, id=channel.channel_name)
            else:
                # If channel is in database, update channel's standup time
                channel = Channel.query.filter_by(channel_name = submitted_channel_name).first()
                channel.standup_time = standup_time
                db.session.commit()
                print("Updated " + submitted_channel_name + "'s standup time to " + str(standup_time))
                # Updating this job's timing
                sched.reschedule_job(channel.channel_name, trigger='cron', day_of_week='mon-fri', hour=0, minute=5)
        else:
            print("Could not update " + submitted_channel_name + "'s standup time to " + str(standup_time))

    return render_template('homepage.html', form=form)


# Setting the standup schedules for already-existing jobs
def set_schedules():
    # Get all rows from our table
    channels_with_scheduled_standups = Channel.query.all()
    # Loop through our results
    for channel in channels_with_scheduled_standups:
        # Add a job for each row in the table
        #sched.add_job(standup_call(channel.channel_name), 'cron', day_of_week='mon-fri', hour=channel.standup_time, id=channel.id)
        print("Channel name that we're setting the schedule for: " + channel.channel_name)
        print("Time: " + str(channel.standup_time))
        sched.add_job(lambda channel.channel_name=channel.channel_name: standup_call(channel.channel_name), 'cron', day_of_week='mon-fri', hour=0, minute=5, id=channel.channel_name)


# Function that triggers the standup call
def standup_call(channel_name):
    print(channel_name)
    result = slack_client.api_call(
      "chat.postMessage",
      channel=str(channel_name),
      text="<!channel> Please reply here with your standup status if you won't be in the office today!",
      username="Standup Bot",
      icon_emoji=":memo:"
    )
    print(result)
    print("Standup alert message sent on " + strftime("%Y-%m-%d %H:%M:%S", localtime()))


if __name__ == '__main__':
    app.run(host='0.0.0.0')

# Setting the scheduling
set_schedules()
# Running the scheduling
sched.start()
print("Standup bot was scheduled on " + strftime("%Y-%m-%d %H:%M:%S", localtime()))
