# Standup Bot by Christina Aiello, 2017
import os
import smtplib
import psycopg2
import re
from slackclient import SlackClient
from time import localtime, strftime
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, Response, jsonify, render_template
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField

app = Flask(__name__)
# To do this just using psycopg2: conn = psycopg2.connect(os.environ['DATABASE_URL'])
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
DB = SQLAlchemy(app)
SCHEDULER = BackgroundScheduler()
SLACK_CLIENT = SlackClient(os.environ['SLACK_BOT_TOKEN'])
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
    timestamp = DB.Column(DB.String(120), unique=False)

    def __init__(self, channel_name, standup_hour, standup_minute, message, email, timestamp):
        self.channel_name = channel_name
        self.standup_hour = standup_hour
        self.standup_minute = standup_minute
        self.message = message
        self.email = email
        self.timestamp = timestamp

    def __repr__(self):
        return '<Channel %r>' % self.channel_name


# Our form model
class StandupSignupForm(Form):
    submitted_channel_name = TextField('Channel Name (Required):', validators=[validators.required()])
    standup_hour = TextField('Standup Hour:')
    standup_minute = TextField('Standup Minute:')
    message = TextField('Standup Message (Will use default message if blank):')
    email = TextField('Where should we email your standup reports? (optional):')


@app.route("/", methods=['GET', 'POST'])
def homepage():
    form = StandupSignupForm(request.form)

    if request.method == 'POST':
        # Get whatever name they gave us for a channel
        submitted_channel_name = request.form['submitted_channel_name']
        standup_hour = remove_starting_zeros_from_time(request.form['standup_hour'])
        standup_minute = remove_starting_zeros_from_time(request.form['standup_minute'])
        message = request.form['message']
        email = request.form['email']
        # If the form field was valid...
        if form.validate():
            # Look for channel in database
            if not DB.session.query(Channel).filter(Channel.channel_name == submitted_channel_name).count():
                # Channel isn't in database. Create our channel object and add it to the database
                channel = Channel(submitted_channel_name, standup_hour, standup_minute, message, email, None)
                DB.session.add(channel)
                DB.session.commit()
                # Adding this additional job to the queue
                SCHEDULER.add_job(trigger_standup_call, 'cron', [channel.channel_name, message], day_of_week='mon-fri', hour=standup_hour, minute=standup_minute, id=channel.channel_name + "_standupcall")
                print(create_logging_label() + "Set " + submitted_channel_name + "'s standup time to " + str(standup_hour) + ":" + format_minutes_to_have_zero(standup_minute) + " with standup message: " + message)
                # Set email job if requested
                if (email != None):
                    set_email_job(channel)

            else:
                # Update channel's standup info (if values weren't empty)
                channel = Channel.query.filter_by(channel_name = submitted_channel_name).first()
                channel.standup_hour = standup_hour if standup_hour != None else channel.standup_hour
                channel.standup_minute = standup_minute if standup_minute != None else channel.standup_minute
                channel.message = message if message != None else channel.message
                channel.email = email if email != None else channel.email
                DB.session.commit()
                # Next we will update the standup message job if one of those values was edited
                if (message != None or standup_hour != None or standup_minute != None):
                    # Updating this job's timing (need to delete and re-add)
                    SCHEDULER.remove_job(submitted_channel_name + "_standupcall")
                    SCHEDULER.add_job(trigger_standup_call, 'cron', [channel.channel_name, channel.message], day_of_week='mon-fri', hour=channel.standup_hour, minute=channel.standup_minute, id=channel.channel_name + "_standupcall")
                    print(create_logging_label() + "Updated " + submitted_channel_name + "'s standup time to " + str(channel.standup_hour) + ":" + format_minutes_to_have_zero(channel.standup_minute) + " with standup message: " + message)
                # Lastly, we update the email job if a change was requested
                if (email != None):
                    set_email_job(channel)
        else:
            print(create_logging_label() + "Could not update standup time. Issue was: " + str(request))

    return render_template('homepage.html', form=form)


# Setting the standup schedules for already-existing jobs
# @return nothing
def set_schedules():
    print(create_logging_label() + "Loading previously-submitted standup data.")
    # Get all rows from our table
    channels_with_scheduled_standups = Channel.query.all()
    # Loop through our results
    for channel in channels_with_scheduled_standups:
        # Add a job for each row in the table, sending standup message to channel
        SCHEDULER.add_job(trigger_standup_call, 'cron', [channel.channel_name, channel.message], day_of_week='mon-fri', hour=channel.standup_hour, minute=channel.standup_minute, id=channel.channel_name + "_standupcall")
        print(create_logging_label() + "Channel name and time that we scheduled standup call for: " + channel.channel_name + " at " + str(channel.standup_hour) + ":" + format_minutes_to_have_zero(channel.standup_minute) + " with message: " + channel.message)
        # Set email job if requested
        set_email_job(channel)


# Function that triggers the standup call.
# <!channel> will create the @channel call.
# Sets a default message if the user doesn't provide one.
# @param channel_name : name of channel to send standup message to
# @param message : (optional) standup message that's sent to channel
# @return nothing
def trigger_standup_call(channel_name, message):
    # Sending our standup message
    result = call_slack_messaging_api(channel_name, message)
    # Evaluating result of call and logging it
    if ("ok" in result):
        print(create_logging_label() + "Standup alert message was sent to " + channel_name)
        print(create_logging_label() + "Result of sending standup message to " + channel_name + " was " + str(result))
        # Getting timestamp for today's standup message for this channel
        channel = Channel.query.filter_by(channel_name = channel_name).first()
        channel.timestamp = result.get("ts")
        DB.session.commit()
    else:
        print(create_logging_label() + "Could not send standup alert message to " + channel_name)


# Will send @param message to @param channel_name
def call_slack_messaging_api(channel_name, message):
    return SLACK_CLIENT.api_call(
      "chat.postMessage",
      channel=str(channel_name),
      text= "<!channel> " + ("Please reply here with your standup status!" if (message == None) else  message),
      username="Standup Bot",
      icon_emoji=":memo:"
    )


# Used to set the email jobs for any old or new channels with standup messages
# @param channel : Channel object from table (has a channel name, email, etc.
#                  See Channel class above.)
# @return nothing
def set_email_job(channel):
    # See if user wanted standups emailed to them
    if (channel.email):
        # Cancel already existing job if it's there
        if channel.channel_name + "_sendemail" in str(SCHEDULER.get_jobs()):
            SCHEDULER.remove_job(channel.channel_name + "_sendemail")
        # Add a job for each row in the table, sending standup replies to chosen email.
        # Sending this at 1pm every day
        SCHEDULER.add_job(get_timestamp_and_send_email, 'cron', [channel.channel_name, channel.email], day_of_week='mon-fri', hour=13, minute=0, id=channel.channel_name + "_sendemail")
        print(create_logging_label() + "Channel that we set email schedule for: " + channel.channel_name)
    else:
        print(create_logging_label() + "Channel " + channel.channel_name + " did not want their standups emailed to them today.")


# Emailing standup results to chosen email address.
# Timestamp comes in after we make our trigger_standup_call.
# @param channel_name : Name of channel whose standup results we want to email to someone
# @param recipient_email_address : Where to send the standup results to
# @return nothing
def get_timestamp_and_send_email(a_channel_name, recipient_email_address):
    channel = Channel.query.filter_by(channel_name = a_channel_name).first()
    if (channel.timestamp != None):
        # First we need to get all replies to this message:
        standups = get_standup_replies_for_message(channel.timestamp, channel.channel_name)
        # If we had replies today...
        if (standups != None):
            # Join the list together so it's easier to read
            formatted_standup_message = ''.join(map(str, standups))
            # Then we need to send an email with this information
            send_email(a_channel_name, recipient_email_address, formatted_standup_message)
            print(create_logging_label() + "Sent " + a_channel_name + "'s standup messages, " + formatted_standup_message + ", to " + recipient_email_address)
            # Finally we need to reset the standup timestamp so we don't get a repeat.
            channel.timestamp = None;
            DB.session.commit()
        else:
            print(create_logging_label() + "Channel " + a_channel_name + " did not have any standup submissions to email today.")
    else:
        # Log that it didn't work
        print(create_logging_label() + "Channel " + a_channel_name + " isn't set up to have standup results sent anywhere because they don't have a timestamp in STANDUP_TIMESTAMP_MAP.")


# Sends an email via our GMAIL account to the chosen email address
def send_email(channel_name, recipient_email_address, email_content):
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.login(os.environ['USERNAME'] + "@gmail.com", os.environ['PASSWORD'])
    message = 'Subject: {}\n\n{}'.format(channel_name + " Standup Report", email_content)
    server.sendmail(STANDUP_MESSAGE_ORIGIN_EMAIL_ADDRESS, recipient_email_address, message)
    server.quit()


# Will fetch the standup messages for a channel
# @param timestamp : A channel's standup message's timestamp (acquired via API)
# @return Standup messages in JSON format
def get_standup_replies_for_message(timestamp, channel_name):
    channel_id = get_channel_id_via_name(channel_name)

    # https://api.slack.com/methods/channels.history
    # "To retrieve a single message, specify its ts value as latest, set
    # inclusive to true, and dial your count down to 1"
    result = SLACK_CLIENT.api_call(
      "channels.history",
      token=os.environ['SLACK_BOT_TOKEN'],
      channel=channel_id,
      latest=timestamp,
      inclusive=True,
      count=1
    )
    # Need to ensure that API call worked
    if ("ok" in result):
        # Only do the following if we actually got replies
        replies = result.get("messages")[0].get("replies")
        if (replies is not None):
            standup_results = []
            for standup_status in replies:
                # Add to our list of standup messages
                standup_results.append(retrieve_standup_reply_info(channel_id, standup_status.get("ts")))
            return standup_results
    else:
        # Log that it didn't work
        print(create_logging_label() + "Tried to retrieve standup results. Could not retrieve standup results for " + channel_name + " due to: " + str(result.error))


# Getting detailed info about this reply, since the initial call
# to the API only gives us the user's ID# and the message's timestamp (ts)
# @param channel_id: ID of the channel whom we're reporting for
# @param standup_status_timestamp: Timestamp for this message
def retrieve_standup_reply_info(channel_id, standup_status_timestamp):
    reply_result = SLACK_CLIENT.api_call(
      "channels.history",
      token=os.environ['SLACK_BOT_TOKEN'],
      channel=channel_id,
      latest=standup_status_timestamp,
      inclusive=True,
      count=1
    )
    # Get username of person who made this reply
    user_result = SLACK_CLIENT.api_call(
      "users.info",
      token=os.environ['SLACK_BOT_TOKEN'],
      user=reply_result.get("messages")[0].get("user")
    )
    print(create_logging_label() + "Adding standup results for " + user_result.get("user").get("real_name"))
    return user_result.get("user").get("real_name") + ": " + reply_result.get("messages")[0].get("text") + "; \n"


# Calls API to get channel ID based on name.
# @param channel_name
# @return channel ID
def get_channel_id_via_name(channel_name):
    channels_list = SLACK_CLIENT.api_call(
      "channels.list",
      token=os.environ['SLACK_BOT_TOKEN']
    )
    print("get_channel_id_via_name " + str(channels_list))
    for channel in channels_list.get("channels"):
        if channel.get("name") == channel_name:
            return channel.get("id")


# ------ Util Functions ------ #


# Used for logging when actions happen
# @return string with logging time
def create_logging_label():
    return strftime("%Y-%m-%d %H:%M:%S", localtime()) + "| "


# For logging purposes
def format_minutes_to_have_zero(minutes):
    if minutes == None:
        return "00"
    else:
        if(int(minutes) < 10):
            return "0" + str(minutes)
        else:
            return str(minutes)


# Scheduler doesn't like zeros at the start of numbers...
# @param time: string to remove starting zeros from
def remove_starting_zeros_from_time(time):
    return (re.search( r'0?(\d+)?', time, re.M|re.I)).group(1)


if __name__ == '__main__':
    app.run(host='0.0.0.0')

# Setting the scheduling
set_schedules()

# Running the scheduling
SCHEDULER.start()

print(create_logging_label() + "Standup bot was started up and scheduled.")
