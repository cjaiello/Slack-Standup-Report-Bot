# Standup Bot by Christina Aiello, 2017
import os
import smtplib
import psycopg2
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, Response, jsonify, render_template
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField
import util
import slack_client
from .channel import Channel

app = Flask(__name__)
# To do this just using psycopg2: conn = psycopg2.connect(os.environ['DATABASE_URL'])
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
DB = SQLAlchemy(app)
SCHEDULER = BackgroundScheduler()
STANDUP_MESSAGE_ORIGIN_EMAIL_ADDRESS = "vistaprintdesignexperience@gmail.com"


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
        standup_hour = util.remove_starting_zeros_from_time(request.form['standup_hour'])
        standup_minute = util.remove_starting_zeros_from_time(request.form['standup_minute'])
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
                add_standup_job(submitted_channel_name, message, standup_hour, standup_minute)
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
                    add_standup_job(channel.channel_name, channel.message, channel.standup_hour, channel.standup_minute)
                # Lastly, we update the email job if a change was requested
                if (email != None):
                    set_email_job(channel)
        else:
            print(util.create_logging_label() + "Could not update standup time. Issue was: " + str(request))

    return render_template('homepage.html', form=form)


# Adds standup job and logs it
def add_standup_job(channel_name, message, standup_hour, standup_minute):
    SCHEDULER.add_job(trigger_standup_call, 'cron', [channel_name, message], day_of_week='mon-fri', hour=standup_hour, minute=standup_minute, id=channel_name + "_standupcall")
    print(util.create_logging_label() + "Set " + channel_name + "'s standup time to " + str(standup_hour) + ":" + util.format_minutes_to_have_zero(standup_minute) + " with standup message: " + message)


# Setting the standup schedules for already-existing jobs
# @return nothing
def set_schedules():
    print(util.create_logging_label() + "Loading previously-submitted standup data.")
    # Get all rows from our table
    channels_with_scheduled_standups = Channel.query.all()
    # Loop through our results
    for channel in channels_with_scheduled_standups:
        # Add a job for each row in the table, sending standup message to channel
        add_standup_job(channel.channel_name, channel.message, channel.standup_hour, channel.standup_minute)
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
    result = slack_client.call_slack_messaging_api(channel_name, message)
    # Evaluating result of call and logging it
    if ("ok" in result):
        print(util.create_logging_label() + "Standup alert message was sent to " + channel_name)
        print(util.create_logging_label() + "Result of sending standup message to " + channel_name + " was " + str(result))
        # Getting timestamp for today's standup message for this channel
        channel = Channel.query.filter_by(channel_name = channel_name).first()
        channel.timestamp = result.get("ts")
        DB.session.commit()
    else:
        print(util.create_logging_label() + "Could not send standup alert message to " + channel_name)


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
        print(util.create_logging_label() + "Channel that we set email schedule for: " + channel.channel_name)
    else:
        print(util.create_logging_label() + "Channel " + channel.channel_name + " did not want their standups emailed to them today.")


# Emailing standup results to chosen email address.
# Timestamp comes in after we make our trigger_standup_call.
# @param channel_name : Name of channel whose standup results we want to email to someone
# @param recipient_email_address : Where to send the standup results to
# @return nothing
def get_timestamp_and_send_email(a_channel_name, recipient_email_address):
    channel = Channel.query.filter_by(channel_name = a_channel_name).first()
    if (channel.timestamp != None):
        # First we need to get all replies to this message:
        standups = slack_client.get_standup_replies_for_message(channel.timestamp, channel.channel_name)
        # If we had replies today...
        if (standups != None):
            # Join the list together so it's easier to read
            formatted_standup_message = ''.join(map(str, standups))
            # Then we need to send an email with this information
            send_email(a_channel_name, recipient_email_address, formatted_standup_message)
            print(util.create_logging_label() + "Sent " + a_channel_name + "'s standup messages, " + formatted_standup_message + ", to " + recipient_email_address)
            # Finally we need to reset the standup timestamp so we don't get a repeat.
            channel.timestamp = None;
            DB.session.commit()
        else:
            print(util.create_logging_label() + "Channel " + a_channel_name + " did not have any standup submissions to email today.")
    else:
        # Log that it didn't work
        print(util.create_logging_label() + "Channel " + a_channel_name + " isn't set up to have standup results sent anywhere because they don't have a timestamp in STANDUP_TIMESTAMP_MAP.")


# Sends an email via our GMAIL account to the chosen email address
def send_email(channel_name, recipient_email_address, email_content):
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.login(os.environ['USERNAME'] + "@gmail.com", os.environ['PASSWORD'])
    message = 'Subject: {}\n\n{}'.format(channel_name + " Standup Report", email_content)
    server.sendmail(STANDUP_MESSAGE_ORIGIN_EMAIL_ADDRESS, recipient_email_address, message)
    server.quit()


if __name__ == '__main__':
    app.run(host='0.0.0.0')

# Setting the scheduling
set_schedules()

# Running the scheduling
SCHEDULER.start()

print(util.create_logging_label() + "Standup bot was started up and scheduled.")
