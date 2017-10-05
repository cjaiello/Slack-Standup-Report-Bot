# Standup Bot by Christina Aiello, 2017. cjaiello@wpi.edu

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, Response, jsonify, render_template
from slackclient import SlackClient
import os
from time import localtime, strftime
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField
import psycopg2
from flask_sqlalchemy import SQLAlchemy
import yagmail

# Used to send emails
yagmail.register(os.environ['USERNAME'], os.environ['PASSWORD'])
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
    standup_hour = db.Column(db.Integer)
    standup_minute = db.Column(db.Integer)
    message = db.Column(db.String(120), unique=False)

    def __init__(self, channel_name, standup_hour, standup_minute, message):
        self.channel_name = channel_name
        self.standup_hour = standup_hour
        self.standup_minute = standup_minute
        self.message = message

    def __repr__(self):
        return '<Channel %r>' % self.channel_name


# Our form model
class StandupSignupForm(Form):
    submitted_channel_name = TextField('Channel Name:', validators=[validators.required()])
    standup_hour = TextField('Standup Hour:', validators=[validators.required()])
    standup_minute = TextField('Standup Minute:', validators=[validators.required()])
    message = TextField('Standup Message:')


@app.route("/", methods=['GET', 'POST'])
def homepage():
    form = StandupSignupForm(request.form)

    if request.method == 'POST':
        # Get whatever name they gave us for a channel
        submitted_channel_name = request.form['submitted_channel_name']
        standup_hour = request.form['standup_hour']
        standup_minute = request.form['standup_minute']
        message = request.form['message']
        # If the form field was valid...
        if form.validate():
            # Look for channel in database
            if not db.session.query(Channel).filter(Channel.channel_name == submitted_channel_name).count():
                # Channel isn't in database. Create our channel object
                channel = Channel(submitted_channel_name, standup_hour, standup_minute, message)
                # Add it to the database
                db.session.add(channel)
                db.session.commit()
                # Adding this additional job to the queue
                sched.add_job(standup_call, 'cron', [channel.channel_name, message], day_of_week='mon-fri', hour=standup_hour, minute=standup_minute, id=channel.channel_name)
                print(create_logging_label() + ": Set " + submitted_channel_name + "'s standup time to " + str(standup_hour) + ":" + str(standup_minute) + " with standup message: " + message)
            else:
                # If channel is in database, update channel's standup time
                channel = Channel.query.filter_by(channel_name = submitted_channel_name).first()
                channel.standup_hour = standup_hour
                channel.standup_minute = standup_minute
                db.session.commit()
                # Updating this job's timing (need to delete and readd)
                sched.remove_job(submitted_channel_name)
                sched.add_job(standup_call, 'cron', [channel.channel_name, message], day_of_week='mon-fri', hour=standup_hour, minute=standup_minute, id=channel.channel_name)
                print(create_logging_label() + ": Updated " + submitted_channel_name + "'s standup time to " + str(standup_hour) + ":" + str(standup_minute) + " with standup message: " + message)
        else:
            print(create_logging_label() + ": Could not update " + submitted_channel_name + "'s standup time to " + str(standup_hour) + ":" + str(standup_minute) + " and message to: " + message + ". Issue was: " + str(request))

    return render_template('homepage.html', form=form)


# Setting the standup schedules for already-existing jobs
def set_schedules():
    # Get all rows from our table
    channels_with_scheduled_standups = Channel.query.all()
    # Loop through our results
    for channel in channels_with_scheduled_standups:
        # Add a job for each row in the table
        sched.add_job(standup_call, 'cron', [channel.channel_name, channel.message], day_of_week='mon-fri', hour=channel.standup_hour, minute=channel.standup_minute, id=channel.channel_name)
        print(create_logging_label() + ": Channel name and time that we set the schedule for: " + channel.channel_name + " at " + str(channel.standup_hour) + ":" + str(channel.standup_minute) + " with message: " + channel.message)


# Function that triggers the standup call.
# <!channel> will create the @channel call.
# Sets a default message if the user doesn't provide one.
def standup_call(channel_name, message):
    result = slack_client.api_call(
      "chat.postMessage",
      channel=str(channel_name),
      text= "<!channel> " + ("Please reply here with your standup status!" if (message == None) else  message),
      username="Standup Bot",
      icon_emoji=":memo:"
    )
    print(create_logging_label() + ": Standup alert message sent to " + channel_name)
    print(create_logging_label() + ": Result of sending standup message to " + channel_name + " was " + str(result))


# Used for logging when actions happen
def create_logging_label():
    return strftime("%Y-%m-%d %H:%M:%S", localtime())


# Emailing standup results to chosen email address
def send_email(squad_name, recipient_email_address):
    email = yagmail.SMTP("vistaprintdesignexperience")
    subject_line = "Daily Standup for " + squad_name + " on " + strftime("%d-%m-%Y", localtime())
    contents = ["Hello world"]
    email.send(recipient_email_address, subject_line, contents)


if __name__ == '__main__':
    app.run(host='0.0.0.0')

# Sending a test email
send_email("test", "christinajaiello@gmail.com")

# Setting the scheduling
set_schedules()
# Running the scheduling
sched.start()
print(create_logging_label() + ": Standup bot was started up and scheduled.")
