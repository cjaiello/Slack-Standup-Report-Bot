# Standup Bot by Christina Aiello, 2017
import os
import smtplib
import psycopg2
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, Response, jsonify, render_template
from wtforms import TextField, TextAreaField, IntegerField, validators, StringField, SubmitField, BooleanField
import util
import slack_client
from flask_wtf import FlaskForm, RecaptchaField
from flask import escape
import email_validator
import logger
import random

app = Flask(__name__)
# To do this just using psycopg2: conn = psycopg2.connect(os.environ['DATABASE_URL'])
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['RECAPTCHA_USE_SSL'] = False
app.config['RECAPTCHA_PUBLIC_KEY'] = os.environ['RECAPTCHA_PUBLIC_KEY']
app.config['RECAPTCHA_PRIVATE_KEY'] = os.environ['RECAPTCHA_PRIVATE_KEY']
app.config['SECRET_KEY'] = os.urandom(32)
DB = SQLAlchemy(app)
SCHEDULER = BackgroundScheduler()

# Our form model
class StandupSignupForm(FlaskForm):
    channel_name = slack_client.get_all_channels()
    standup_hour = IntegerField('Standup Hour:', validators=[validators.NumberRange(min=0, max=12)])
    standup_minute = IntegerField('Standup Minute:', validators=[validators.NumberRange(min=0, max=59)])
    am_or_pm = ['pm', 'am']
    message = TextField('Standup Message (Will use default message if blank):')
    email = TextField('Where should we email your standup reports? (optional):', validators=[validators.Email(), validators.Optional()])
    recaptcha = RecaptchaField()
    csrf = app.config['SECRET_KEY']
    confirmation_code = TextField()
    email_confirmed = BooleanField()

class EmailConfirmationForm(FlaskForm):
    code = TextField(validators=[validators.Required()])
    recaptcha = RecaptchaField()
    csrf = app.config['SECRET_KEY']

@app.route("/", methods=['GET', 'POST'])
def homepage():
    form = StandupSignupForm()
    response_message = None

    if request.method == 'POST':
        logger.log("Someone posted a form: " + request.remote_addr, "INFO") # Issue 25: eventType: ProcessingForm
        logger.log("Made the form object with form values", "INFO") # Issue 25: eventType: ProcessingForm
        # Get whatever info they gave us for their channel
        # TODO: You don't need to make all these variables... 
        # just set them on the form object and pass around the form
        submitted_channel_name = escape(request.form['channel_name'])
        standup_hour = util.remove_starting_zeros_from_time(
            escape(request.form['standup_hour']))
        standup_minute = util.remove_starting_zeros_from_time(
            escape(request.form['standup_minute']))
        message = escape(request.form['message'])
        email = escape(request.form['email'])
        am_or_pm = escape(request.form['am_or_pm'])
        confirmation_code = generate_code()
        logger.log("Pulled values from form", "INFO") # Issue 25: eventType: ProcessingForm  
        # If the form field was valid...
        if form.validate_on_submit():
            # Look for channel in database
            logger.log("Form was valid upon submit", "INFO") # Issue 25: eventType: ProcessingForm
            if not DB.session.query(Channel).filter(Channel.channel_name == submitted_channel_name).count():
                logger.log("Add new channel to DB", "INFO") # Issue 25: eventType: ProcessingForm
                add_channel_standup_schedule(submitted_channel_name, standup_hour, standup_minute, message, email, am_or_pm, False, confirmation_code)
                send_email(submitted_channel_name, email, "Your confirmation code is " + confirmation_code + " https://daily-stand-up-bot.herokuapp.com/confirm_email?email=" + email + "&channel_name=" + submitted_channel_name)
            else:
                # Update channel's standup info
                logger.log("Update channel's standup info", "INFO") # Issue 25: eventType: ProcessingForm
                update_channel_standup_schedule(submitted_channel_name, standup_hour, standup_minute, message, email, am_or_pm, False, confirmation_code)
                send_email(submitted_channel_name, email, "Your confirmation code is " + confirmation_code + " https://daily-stand-up-bot.herokuapp.com/confirm_email?email=" + email + "&channel_name=" + submitted_channel_name)
            response_message = "Success! Standup bot scheduling set for " + submitted_channel_name + " at " + str(standup_hour) + ":" + util.format_minutes_to_have_zero(standup_minute) + am_or_pm + " with reminder message " + message
            response_message += " and responses being emailed to " + email if (email) else "" + ". To receive your standup report in an email, please log into your email and click the link and enter the code in the email we just sent you to confirm ownership of this email."
            slack_client.send_confirmation_message(submitted_channel_name, response_message)
        else:
            logger.log("Could not update standup time.", "ERROR") # Issue 25: eventType: ProcessingForm
            logger.log(str(form.errors), "ERROR") # Issue 25: eventType: ProcessingForm
            response_message = "Please fix the error(s) below"

    return render_template('homepage.html', form=form, message=response_message)

@app.route("/confirm_email", methods=['GET', 'POST'])
def confirm_email():
    form = EmailConfirmationForm()
    response_message = None
    email = request.args.get('email', default = None)
    channel_name = request.args.get('channel_name', default = None)
    logger.log("channel_name: " + channel_name, "INFO") # Issue 25: eventType: ConfirmEmail

    if request.method == 'POST':
        form = EmailConfirmationForm(request.form)
        code = request.form['code']
        if form.validate_on_submit() and email:
            channel = Channel.query.filter_by(email=email, channel_name=channel_name).first()
            logger.log("Email address being confirmed is: " + str(channel.email), "INFO") # Issue 25: eventType: ConfirmEmail
            logger.log("Code submitted was: " + str(code), "INFO") # Issue 25: eventType: ConfirmEmail
            logger.log("confirmation_code was: " + str(channel.confirmation_code), "INFO") # Issue 25: eventType: ConfirmEmail
            logger.log("Type of Code submitted was: " + str(type(code)), "INFO") # Issue 25: eventType: ConfirmEmail
            logger.log("Type of confirmation_code was: " + str(type(channel.confirmation_code)), "INFO") # Issue 25: eventType: ConfirmEmail
            if (code == channel.confirmation_code):
                channel.email_confirmed = True
                DB.session.add(channel)
                DB.session.commit()
                response_message = "Email " + channel.email + " has been confirmed! You will now be emailed your standup reports."
                logger.log("Email address being confirmed is: " + channel.email, "INFO") # Issue 25: eventType: ConfirmEmail
                return render_template('homepage.html', form=StandupSignupForm(), message=response_message)
            else:
                logger.log("Could not validate form because code != channel.confirmation_code", "ERROR") # Issue 25: eventType: ConfirmEmail
                response_message = "Form submission failed. Please try again."
                return render_template('confirm_email.html', form=form, message=response_message)
        else:
            logger.log("Could not validate form because: " + str(form.errors), "ERROR") # Issue 25: eventType: ConfirmEmail
            response_message = "Form submission failed. Please try again."
            return render_template('confirm_email.html', form=form, message=response_message)
    else:
        return render_template('confirm_email.html', form=form, message=None)

def update_channel_standup_schedule(submitted_channel_name, standup_hour, standup_minute, message, email, am_or_pm, email_confirmed, confirmation_code):
    channel = Channel.query.filter_by(
        channel_name=submitted_channel_name).first()
    channel.standup_hour = util.calculate_am_or_pm(
        standup_hour, am_or_pm) if standup_hour != None else channel.standup_hour
    channel.standup_minute = standup_minute if standup_minute != None else channel.standup_minute
    channel.message = message if message != None else channel.message
    channel.email = email if email != None else channel.email
    channel.confirmation_code = confirmation_code if confirmation_code != None else channel.confirmation_code
    DB.session.add(channel)
    DB.session.commit()
    # Next we will update the standup message job if one of those values was edited
    if (message != None or standup_hour != None or standup_minute != None):
        # Updating this job's timing (need to delete and re-add)
        SCHEDULER.remove_job(
            submitted_channel_name + "_standupcall")
        add_standup_job(channel.channel_name, channel.message,
                        channel.standup_hour, channel.standup_minute)
    # Lastly, we update the email job if a change was requested
    if (email != None):
        set_email_job(channel)

def add_channel_standup_schedule(submitted_channel_name, standup_hour, standup_minute, message, email, am_or_pm, email_confirmed, confirmation_code):
    # Channel isn't in database. Create our channel object and add it to the database
    channel = Channel(submitted_channel_name, util.calculate_am_or_pm(
        standup_hour, am_or_pm), standup_minute, message, email, None, False, confirmation_code)
    logger.log("Made channel object", "INFO") # Issue 25: eventType: AddChannelStandupScheduleToDb
    DB.session.add(channel)
    logger.log("Added into DB session", "INFO") # Issue 25: eventType: AddChannelStandupScheduleToDb
    DB.session.commit()
    logger.log("Committed to DB session", "INFO") # Issue 25: eventType: AddChannelStandupScheduleToDb
    # Adding this additional job to the queue
    add_standup_job(submitted_channel_name, message, util.calculate_am_or_pm(
        standup_hour, am_or_pm), standup_minute)
    logger.log("Added email job to scheduler. Now going to set email job", "INFO") # Issue 25: eventType: AddChannelStandupScheduleToDb
    # Set email job if requested
    if (email != None):
        set_email_job(channel)

# Adds standup job and logs it
def add_standup_job(channel_name, message, standup_hour, standup_minute):
    logger.log("Adding standup to scheduler " + " \n Channel name: " + channel_name + " \n Message: " + message + "\n Standup_hour: " + str(standup_hour) + "\n Standup_minute: " + str(standup_minute), "INFO") # Issue 25: eventType: AddChannelStandupJob
    SCHEDULER.add_job(trigger_standup_call, 'cron', [
                      channel_name, message], day_of_week='mon-fri', hour=standup_hour, minute=standup_minute, id=channel_name + "_standupcall")
    logger.log("Set " + channel_name + "'s standup time to " + str(standup_hour) +
          ":" + util.format_minutes_to_have_zero(standup_minute) + " with standup message: " + message, "INFO") # Issue 25: eventType: AddChannelStandupJob


# Setting the standup schedules for already-existing jobs
# @return nothing
def set_schedules():
    logger.log("Loading previously-submitted standup data.", "INFO") # Issue 25: eventType: SettingSchedule
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
    result = slack_client.send_standup_message(channel_name, message)
    # Evaluating result of call and logging it
    logger.log("Result of sending standup message to " + channel_name + " was " + str(result), "INFO") # Issue 25: eventType: TriggerStandupMessage
    if (result["ok"]):
        logger.log("Standup alert message was sent to " + channel_name, "INFO") # Issue 25: eventType: TriggerStandupMessage
        # Getting timestamp for today's standup message for this channel
        channel = Channel.query.filter_by(channel_name=channel_name).first()
        channel.timestamp = result["ts"]
        DB.session.commit()
    else:
        logger.log("Could not send standup alert message to " + channel_name, "ERROR") # Issue 25: eventType: TriggerStandupMessage


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
        SCHEDULER.add_job(get_timestamp_and_send_email, 'cron', [
                          channel.channel_name, channel.email], day_of_week='mon-fri', hour=int(channel.standup_hour), minute=int(channel.standup_minute) + 1, id=channel.channel_name + "_sendemail")
        logger.log("Channel that we set email schedule for: " + channel.channel_name, "INFO") # Issue 25: eventType: CreateEmailJob
    else:
        logger.log("Channel " + channel.channel_name +
              " did not want their standups emailed to them today.", "INFO") # Issue 25: eventType: CreateEmailJob


# Emailing standup results to chosen email address.
# Timestamp comes in after we make our trigger_standup_call.
# @param channel_name : Name of channel whose standup results we want to email to someone
# @param recipient_email_address : Where to send the standup results to
# @return nothing
def get_timestamp_and_send_email(a_channel_name, recipient_email_address):
    channel = Channel.query.filter_by(channel_name=a_channel_name).first()
    if (channel.timestamp != None and channel.email_confirmed):
        # First we need to get all replies to this message:
        standups = slack_client.get_standup_replies_for_message(
            channel.timestamp, channel.channel_name)
        # If we had replies today...
        if (standups != None):
            # Join the list together so it's easier to read
            formatted_standup_message = ''.join(map(str, standups))
            # Then we need to send an email with this information
            send_email(a_channel_name, recipient_email_address,
                       formatted_standup_message)
            logger.log("Sent " + a_channel_name + "'s standup messages, " +
                  formatted_standup_message + ", to " + recipient_email_address, "INFO") # Issue 25: eventType: SendStandupEmail
            # Finally we need to reset the standup timestamp so we don't get a repeat.
            channel.timestamp = None
            DB.session.commit()
        else:
            logger.log("Channel " + a_channel_name +
                  " did not have any standup submissions to email today.", "INFO") # Issue 25: eventType: SendStandupEmail
    else:
        # Log that it didn't work
        logger.log("Channel " + a_channel_name +
              " isn't set up to have standup results sent anywhere because they don't have a timestamp in STANDUP_TIMESTAMP_MAP or haven't confirmed their email.", "ERROR") # Issue 25: eventType: SendStandupEmail


# Sends an email via our GMAIL account to the chosen email address
def send_email(channel_name, recipient_email_address, email_content):
    logger.log("Email info: " + str(channel_name) + " | " + str(recipient_email_address) + " | " + email_content, "INFO")
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.login(os.environ['USERNAME'], os.environ['PASSWORD'])
    logger.log("Username is " + os.environ['USERNAME'], 'INFO') # Issue 25: eventType: SendEmail
    message = 'Subject: {}\n\n{}'.format(channel_name + " Standup Report", email_content)
    logger.log(message, "INFO")
    server.sendmail(os.environ['USERNAME'], recipient_email_address, message)
    server.quit()


# Generate a random 6-digit code
def generate_code():
  code = ""
  for i in range (1, 7):
    code += (str(random.randrange(10)))
  return code


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
    email_confirmed = DB.Column(DB.Integer)
    confirmation_code = DB.Column(DB.String(6), unique=False)

    def __init__(self, channel_name, standup_hour, standup_minute, message, email, timestamp, email_confirmed, confirmation_code):
        self.channel_name = channel_name
        self.standup_hour = standup_hour
        self.standup_minute = standup_minute
        self.message = message
        self.email = email
        self.timestamp = timestamp
        self.email_confirmed = email_confirmed
        self.confirmation_code = confirmation_code

    def __repr__(self):
        return '<Channel %r>' % self.channel_name


if __name__ == '__main__':
    app.run(host='0.0.0.0')

# Setting the scheduling
set_schedules()

# Running the scheduling
SCHEDULER.start()

logger.log("Standup bot was started up and scheduled.", "INFO") # Issue 25: eventType: Startup
