# Standup Bot by Christina Aiello, 2017. cjaiello@wpi.edu
import os
import smtplib
import psycopg2
from slackclient import SlackClient
from time import localtime, strftime
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, Response, jsonify, render_template
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
DB = SQLAlchemy(app)
SCHEDULER = BackgroundScheduler()
SLACK_CLIENT = SlackClient(os.environ['SLACK_BOT_TOKEN'])
STANDUP_TIMESTAMP_MAP = {} # Holds channel names and their day's timestamp (needed to get replies)
STANDUP_MESSAGE_ORIGIN_EMAIL_ADDRESS = "vistaprintdesignexperience@gmail.com"

# Create our database model
class Channel(DB.Model):
    __tablename__ = "channel"
    id = DB.Column(DB.Integer, primary_key=True)
    channel_name = DB.Column(DB.String(120), unique=True)
    standup_hour = DB.Column(DB.Integer)
    standup_minute = DB.Column(DB.Integer)
    message = DB.Column(DB.String(120), unique=False)
    email = DB.Column(DB.String(120), unique=False)

    def __init__(self, channel_name, standup_hour, standup_minute, message, email):
        self.channel_name = channel_name
        self.standup_hour = standup_hour
        self.standup_minute = standup_minute
        self.message = message
        self.email = email

    def __repr__(self):
        return '<Channel %r>' % self.channel_name


# Our form model
class StandupSignupForm(Form):
    submitted_channel_name = TextField('Channel Name:', validators=[validators.required()])
    standup_hour = TextField('Standup Hour:', validators=[validators.required()])
    standup_minute = TextField('Standup Minute:', validators=[validators.required()])
    message = TextField('Standup Message (Optional. Will use default message if blank.):')
    email = TextField('Email Address to Send Standup Report To (Optional):')


@app.route("/", methods=['GET', 'POST'])
def homepage():
    form = StandupSignupForm(request.form)

    if request.method == 'POST':
        # Get whatever name they gave us for a channel
        submitted_channel_name = request.form['submitted_channel_name']
        standup_hour = request.form['standup_hour']
        standup_minute = request.form['standup_minute']
        message = request.form['message']
        email = request.form['email']
        # If the form field was valid...
        if form.validate():
            # Look for channel in database
            if not DB.session.query(Channel).filter(Channel.channel_name == submitted_channel_name).count():
                # Channel isn't in database. Create our channel object
                channel = Channel(submitted_channel_name, standup_hour, standup_minute, message, email)
                # Add it to the database
                DB.session.add(channel)
                DB.session.commit()
                # Adding this additional job to the queue
                SCHEDULER.add_job(standup_call, 'cron', [channel.channel_name, message], day_of_week='mon-fri', hour=standup_hour, minute=standup_minute, id=channel.channel_name)
                print(create_logging_label() + "Set " + submitted_channel_name + "'s standup time to " + str(standup_hour) + ":" + str(standup_minute) + " with standup message: " + message)
                # Set email job if requested
                set_email_job(channel)

            else:
                # If channel is in database, update channel's standup time
                channel = Channel.query.filter_by(channel_name = submitted_channel_name).first()
                channel.standup_hour = standup_hour
                channel.standup_minute = standup_minute
                DB.session.commit()
                # Updating this job's timing (need to delete and readd)
                SCHEDULER.remove_job(submitted_channel_name)
                SCHEDULER.add_job(standup_call, 'cron', [channel.channel_name, message], day_of_week='mon-fri', hour=standup_hour, minute=standup_minute, id=channel.channel_name)
                print(create_logging_label() + "Updated " + submitted_channel_name + "'s standup time to " + str(standup_hour) + ":" + str(standup_minute) + " with standup message: " + message)
                # Set email job if requested
                set_email_job(channel)
        else:
            print(create_logging_label() + "Could not update " + submitted_channel_name + "'s standup time to " + str(standup_hour) + ":" + str(standup_minute) + " and message to: " + message + ". Issue was: " + str(request))

    return render_template('homepage.html', form=form)


# Setting the standup schedules for already-existing jobs
def set_schedules():
    # Get all rows from our table
    channels_with_scheduled_standups = Channel.query.all()
    # Loop through our results
    for channel in channels_with_scheduled_standups:
        # Add a job for each row in the table, sending standup message to channel
        SCHEDULER.add_job(standup_call, 'cron', [channel.channel_name, channel.message], day_of_week='mon-fri', hour=channel.standup_hour, minute=channel.standup_minute, id=channel.channel_name)
        print(create_logging_label() + "Channel name and time that we set the schedule for: " + channel.channel_name + " at " + str(channel.standup_hour) + ":" + str(channel.standup_minute) + " with message: " + channel.message)
        # Set email job if requested
        set_email_job(channel)


# Function that triggers the standup call.
# <!channel> will create the @channel call.
# Sets a default message if the user doesn't provide one.
# @param channel_name : name of channel to send standup message to
# @param message : (optional) standup message that's sent to channel
def standup_call(channel_name, message):
    # Emptying our set of channel names and timestamps to avoid repeats
    STANDUP_TIMESTAMP_MAP = {}
    # Sending our standup message
    result = SLACK_CLIENT.api_call(
      "chat.postMessage",
      channel=str(channel_name),
      text= "<!channel> " + ("Please reply here with your standup status!" if (message == None) else  message),
      username="Standup Bot",
      icon_emoji=":memo:"
    )
    # Evaluating result of call and logging it
    if (result.ok):
        print(create_logging_label() + "Standup alert message sent to " + channel_name)
        print(create_logging_label() + "Result of sending standup message to " + channel_name + " was " + str(result))
        # Getting timestamp for today's standup message for this channel
        STANDUP_TIMESTAMP_MAP[channel_name] = result.ts
    else:
        print(create_logging_label() + "Could not send standup alert message to " + channel_name)


# Used to set the email jobs for any old or new channels with standup messages
# @param channel : Channel object from table (has a channel name, email, etc.
#                  See Channel class above.)
def set_email_job(channel):
    # See if user wanted standups emailed to them
    if (channel.email):
        # Add a job for each row in the table, sending standup replies to chosen email.
        # Sending this at 1pm every day
        SCHEDULER.add_job(get_timestamp_and_send_email, 'cron', [channel.channel_name, channel.email], day_of_week='mon-fri', hour=13, id=channel.channel_name)
        print(create_logging_label() + "Channel name and time that we set email schedule for: " + channel.channel_name)
    else:
        print(create_logging_label() + "Channel " + channel.channel_name + " did not want their standups emailed to them today.")


# Used for logging when actions happen
def create_logging_label():
    return strftime("%Y-%m-%d %H:%M:%S", localtime()) + ""


# Emailing standup results to chosen email address
# @param channel_name : Name of channel whose standup results we want to email to someone
# @param recipient_email_address : Where to send the standup results to
def get_timestamp_and_send_email(channel_name, recipient_email_address):
    if (STANDUP_TIMESTAMP_MAP[channel_name]):
        # First, we need to get this squad's standup message timestamp for the day
        standup_message_timestamp = STANDUP_TIMESTAMP_MAP[channel_name]

        # Next we need to get all replies to this message:
        get_daily_standups(standup_message_timestamp)

        # Lastly we need to send an email with this information
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.login(os.environ['USERNAME'] + "@gmail.com", os.environ['PASSWORD'])
        msg = "YOUR MESSAGE!" # TODO: Replace with actual message attached to channel
        server.sendmail(STANDUP_MESSAGE_ORIGIN_EMAIL_ADDRESS, recipient_email_address, msg)
        server.quit()
    else:
        # Log that it didn't work
        print(create_logging_label() + "Channel " + channel_name + " isn't set up to have standup results sent anywhere.")


# Will fetch all standup message timestamps
# @param timestamp : A channel's standup message's timestamp (acquired via API)
def get_daily_standups(timestamp):
    # https://api.slack.com/methods/channels.history
    # "To retrieve a single message, specify its ts value as latest, set
    # inclusive to true, and dial your count down to 1"
    result = SLACK_CLIENT.api_call(
      "channels.history",
      token=os.environ['SLACK_BOT_TOKEN'],
      channel=str(channel_name),
      oldest=timestamp,
      ts="latest",
      inclusive=true,
      count=1
    )
    if (result.ok):
        # Get replies from it
        console.log(str(result))
        # TODO: Get the replies from this thread
    else:
        # Log that it didn't work
        print(create_logging_label() + "Could not email standup results to " + channel_name + " due to: " + str(result))



if __name__ == '__main__':
    app.run(host='0.0.0.0')

# Sending a test email to myself. I swear I have friends.
get_timestamp_and_send_email("christinastestchannel", "christinajaiello@gmail.com")

# Setting the scheduling
set_schedules()

# Running the scheduling
SCHEDULER.start()
print(create_logging_label() + "Standup bot was started up and scheduled.")
