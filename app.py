# Standup Bot by Christina Aiello, 2017-2020
import os
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
from logger import Logger
import html
from profanity_filter import ProfanityFilter
import email_client

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['RECAPTCHA_USE_SSL'] = False
app.config['RECAPTCHA_PUBLIC_KEY'] = os.environ['RECAPTCHA_PUBLIC_KEY']
app.config['RECAPTCHA_PRIVATE_KEY'] = os.environ['RECAPTCHA_PRIVATE_KEY']
app.config['SECRET_KEY'] = os.urandom(32)
DB = SQLAlchemy(app)
SCHEDULER = BackgroundScheduler()
PF = ProfanityFilter()

# Our form model
class StandupSignupForm(FlaskForm):
    channel_name = slack_client.get_all_channels()
    standup_hour = IntegerField('Standup Hour:', validators=[validators.NumberRange(min=0, max=12)])
    standup_minute = IntegerField('Standup Minute:', validators=[validators.NumberRange(min=0, max=59)])
    hours_delay = IntegerField('Number of Hours Until Standup Closes:', validators=[validators.Optional(), validators.NumberRange(min=0, max=23)])
    minutes_delay = IntegerField('Number of Minutes Until Standup Closes:', validators=[validators.Optional(), validators.NumberRange(min=0, max=59)])
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
        Logger.log("Someone posted a form: " + request.remote_addr, Logger.info) # Issue 25: eventType: ProcessingForm
        standup_form = {
            'channel_name' : str(escape(request.form['channel_name'])),
            'standup_hour' :  util.remove_starting_zeros_from_time(escape(request.form['standup_hour'])),
            'standup_minute' :  util.remove_starting_zeros_from_time(escape(request.form['standup_minute'])),
            'hours_delay' :  util.remove_starting_zeros_from_time(escape(request.form['hours_delay'])),
            'minutes_delay' :  util.remove_starting_zeros_from_time(escape(request.form['minutes_delay'])),
            'message' :  str(escape(filter_standup_message(str(request.form['message'])))),
            'email' :  str(escape(request.form['email'])),
            'am_or_pm' :  str(escape(request.form['am_or_pm'])),
            'confirmation_code' :  util.generate_code()
        }
        Logger.log("Pulled values from form", Logger.info) # Issue 25: eventType: ProcessingForm  
        # If the form field was valid...
        if form.validate_on_submit():
            channel = None # Default to None
            # Look for channel in database
            Logger.log("Form was valid upon submit", Logger.info) # Issue 25: eventType: ProcessingForm
            if not DB.session.query(Channel).filter(Channel.channel_name == standup_form['channel_name']).count():
                # Add our new channel to the database
                Logger.log("Add new channel to DB", Logger.info) # Issue 25: eventType: ProcessingForm
                channel = add_channel(standup_form)
            else:
                # Update channel's standup info in the database
                Logger.log("Update channel's standup info", Logger.info) # Issue 25: eventType: ProcessingForm
                channel = update_channel(standup_form)
            if standup_form['email'] and not channel.email_confirmed:
                Logger.log("We need email confirmation for email " + standup_form['email'], Logger.info) # Issue 25: eventType: ProcessingForm
                link_to_confirm_email = "https://daily-stand-up-bot.herokuapp.com/confirm_email?email=" + standup_form['email'] + "&channel_name=" + standup_form['channel_name']
                confirm_email_message = "Thank you for using Daily Standup Bot! https://daily-stand-up-bot.herokuapp.com/! \n If you did not sign up on our website, please disregard this email. \n\n Your confirmation code is " + standup_form['confirmation_code'] + ". Please go to this link and submit your code to confirm your email: " + link_to_confirm_email
                email_client.send_email(standup_form['channel_name'], standup_form['email'], confirm_email_message, "Confirm Email Address for Standup Report")
            response_message = confirm_success(standup_form, channel.email_confirmed, channel.email)
        else:
            # If the form was NOT valid...
            Logger.log("Could not update standup time.", Logger.error) # Issue 25: eventType: ProcessingForm
            Logger.log(str(form.errors), Logger.error) # Issue 25: eventType: ProcessingForm
            response_message = "Please fix the error(s) below"

    return render_template('homepage.html', form=form, message=response_message)


@app.route("/confirm_email", methods=['GET', 'POST'])
def confirm_email():
    form = EmailConfirmationForm()
    response_message = None
    Logger.log("request.args: " + str(request.args), Logger.info) # Issue 25: eventType: ConfirmEmail
    email = request.args.get('email', default = None)
    channel_name = request.args.get('channel_name', default = None)
    Logger.log("channel_name: " + channel_name, Logger.info) # Issue 25: eventType: ConfirmEmail

    if request.method == 'POST':
        form = EmailConfirmationForm(request.form)
        code = request.form['code']
        if form.validate_on_submit() and email:
            # Go into the database and get our channel object based on email address and channel name.
            channel = Channel.query.filter_by(email=email, channel_name=channel_name).first()
            Logger.log("Email address being confirmed is: " + str(channel.email) + " | Code submitted was: " + str(code) + " | Confirmation_code was: " + str(channel.confirmation_code), Logger.info) # Issue 25: eventType: ConfirmEmail
            if (code == channel.confirmation_code):
                channel.email_confirmed = True
                DB.session.add(channel)
                DB.session.commit()
                response_message = "Email " + channel.email + " has been confirmed! You will now be emailed your standup reports."
                Logger.log("Email address confirmed was: " + channel.email, Logger.info) # Issue 25: eventType: ConfirmEmail
                return render_template('homepage.html', form=StandupSignupForm(), message=response_message)
            else:
                Logger.log("Could not validate form because code != channel.confirmation_code", Logger.error) # Issue 25: eventType: ConfirmEmail
                response_message = "Form submission failed. Please try again."
        else:
            Logger.log("Could not validate form because: " + str(form.errors), Logger.error) # Issue 25: eventType: ConfirmEmail
            response_message = "Form submission failed. Please try again."
    return render_template('confirm_email.html', form=form, message=response_message)


# Updates standup schedules for a previously-submitted channel
# @param form : User's input in form form
def update_channel(form):
    channel = Channel.query.filter_by(channel_name=form['channel_name']).first()
    Logger.log("Updating channel " + str(channel.channel_name), Logger.info) # Issue 25: eventType: AddChannelStandupScheduleToDb
    
    channel.standup_hour = util.calculate_am_or_pm(form['standup_hour'], form['am_or_pm'])
    channel.standup_minute = form['standup_minute']
    channel.hours_delay = form['hours_delay']
    channel.minutes_delay = form['minutes_delay']
    channel.message = form['message']

    # If you change the email address, you need to re-confirm that email address with a new code
    if (form['email'] != channel.email):
        Logger.log("Form email " + str(form['email']) + " not equal to channel's current email: " + str(channel.channel_name), Logger.info) # Issue 25: eventType: AddChannelStandupScheduleToDb
        channel.email = form['email']
        if (form['email'] != None and form['email'] != ""):
            Logger.log("Form email wasn't none: " + str(form['email']) + ", so we need to reset the confirmation code and email confirmed field", Logger.info) # Issue 25: eventType: AddChannelStandupScheduleToDb
            channel.confirmation_code = form['confirmation_code']
            channel.email_confirmed = False
        else:
            channel.email_confirmed = True # Nothing to confirm, so don't let this be a blocker anywhere else
    update_email_job(channel)

    DB.session.add(channel)
    DB.session.commit()

    # Updating this job's timing (need to delete and re-add)
    SCHEDULER.remove_job(channel.channel_name + "_standupcall")
    add_standup_job(channel)

    Logger.log("channel.email_confirmed is: " + str(channel.email_confirmed) + " and not that is: " + str((not channel.email_confirmed)), Logger.info) # Issue 25: eventType: AddChannelStandupScheduleToDb
                
    return channel


# Adds standup schedules for a new channel
# @param form : User's input in form form
def add_channel(form):
    channel = Channel(form['channel_name'], util.calculate_am_or_pm(form['standup_hour'], form['am_or_pm']), form['standup_minute'], form['message'], form['email'], None, False, form['confirmation_code'], form['hours_delay'], form['minutes_delay'])
    DB.session.add(channel)
    DB.session.commit()
    Logger.log("Committed channel " + form['channel_name'] + " to DB session", Logger.info) # Issue 25: eventType: AddChannelStandupScheduleToDb
    # Adding this additional job to the queue
    add_standup_job(channel)
    Logger.log("Added email job to scheduler. Now going to set email job", Logger.info) # Issue 25: eventType: AddChannelStandupScheduleToDb
    # Set email job if requested
    if (form['email'] != None and form['email'] != ""):
        Logger.log("New channel, " + form['channel_name'] + ", needs its email job set up to email " + form['email'], Logger.info) # Issue 25: eventType: AddChannelStandupScheduleToDb
        update_email_job(channel)
    return channel


# Adds standup job and logs it
# @return nothing
def add_standup_job(channel):
    Logger.log("Adding standup to scheduler " + " | Channel name: " + channel.channel_name + " | standup_message: " + channel.message + " | hour: " + str(channel.standup_hour) + " | minute: " + str(channel.standup_minute), Logger.info) # Issue 25: eventType: AddChannelStandupJob
    SCHEDULER.add_job(trigger_standup_call, 'cron', [
                      channel.channel_name, channel.message], day_of_week='mon-sun', hour=channel.standup_hour, minute=channel.standup_minute, id=channel.channel_name + "_standupcall")
    Logger.log("Set " + channel.channel_name + "'s standup time to " + str(channel.standup_hour) +
          ":" + util.format_minutes_to_have_zero(channel.standup_minute) + " with standup standup_message: " + channel.message, Logger.info) # Issue 25: eventType: AddChannelStandupJob


# Sends Slack confirmation message indicating success
# @param form: form inputs
# @param must_confirm_email : Whether or not there was an email address submitted that needs to be confirmed
# @return Message to display on page
def confirm_success(form, email_confirmed, email):
    response_message = "Success! Standup bot scheduling set for " + form['channel_name'] + " at " + str(form['standup_hour']) + ":" + util.format_minutes_to_have_zero(form['standup_minute']) + form['am_or_pm'] + " with reminder message '" + form['message'] + "'."
    if form['hours_delay'] or form['minutes_delay']:
        potential_minutes_text = ((str(form['minutes_delay']) + " minutes") if form['minutes_delay'] and int(form['minutes_delay']) > 1 else "") + ((str(form['minutes_delay']) + " minute") if form['minutes_delay'] and int(form['minutes_delay']) == 1 else "")
        potential_hours_text = ((str(form['hours_delay']) + " hours") if form['hours_delay'] else "")
        potential_and_text = (" and " if form['hours_delay'] and form['minutes_delay'] else "")
        response_message += " You have given the channel " + potential_hours_text + potential_and_text + potential_minutes_text + " to submit their standup status."
    else:
        response_message += " By default you have given the channel one hour to submit their standup status."
    if email:
        response_message += " Responses will be emailed to " + email + "."
        if not email_confirmed:
            response_message += " To receive your standup report in an email, please confirm ownership of this email address by going to your inbox, clicking on the link in the email that we just sent you, and entering the code that was in the email."
    slack_client.send_confirmation_message(form['channel_name'], response_message)
    return response_message
    
    
# Setting the standup schedules for already-existing jobs
# @return nothing
def set_schedules():
    Logger.log("Loading previously-submitted standup data.", Logger.info) # Issue 25: eventType: SettingSchedule
    # Get all rows from our table
    channels_with_scheduled_standups = Channel.query.all()
    # Loop through our results
    for channel in channels_with_scheduled_standups:
        # Add a job for each row in the table, sending standup message to channel
        add_standup_job(channel)
        # Set email job if requested
        update_email_job(channel)


# Filters message if profane and logs when profanity filter is needed
# @param message : User input for standup message
# @return User's message, censored
def filter_standup_message(original_message):
    if (PF.is_profane(original_message)):
        censored_message = PF.censor(original_message)
        Logger.log("Censoring standup message. | Message was: " + original_message + " | Message is now: " + censored_message, Logger.info) # Issue 25: eventType: AddChannelStandupScheduleToDb
        return censored_message
    else:
        return original_message


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
    Logger.log("Result of sending standup message to " + channel_name + " was " + str(result), Logger.info) # Issue 25: eventType: TriggerStandupMessage
    if (result["ok"]):
        Logger.log("Standup alert message was sent to " + channel_name, Logger.info) # Issue 25: eventType: TriggerStandupMessage
        # Getting timestamp for today's standup message for this channel
        channel = Channel.query.filter_by(channel_name=channel_name).first()
        channel.timestamp = result["ts"]
        DB.session.commit()
    else:
        Logger.log("Could not send standup alert message to " + channel_name, Logger.error) # Issue 25: eventType: TriggerStandupMessage


# Used to set the email jobs for any old or new channels with standup messages
# @param channel : Channel object from table (has a channel name, email, etc.
#                  See Channel class above.)
# @return nothing
def update_email_job(channel):
    # Cancel already-existing job if it's there
    if channel.channel_name + "_sendemail" in str(SCHEDULER.get_jobs()):
        SCHEDULER.remove_job(channel.channel_name + "_sendemail")
        Logger.log("Channel " + channel.channel_name + " is having their old email job removed.", Logger.info) # Issue 25: eventType: CreateOrUpdateEmailJob

    # See if user wanted standups emailed to them
    if (channel.email):
        # Add a job for each row in the table, sending standup replies to chosen email.
        did_not_enter_hours = channel.hours_delay == "" or channel.hours_delay == None
        did_not_enter_minutes = channel.minutes_delay == "" or channel.minutes_delay == None
        if did_not_enter_hours and did_not_enter_minutes:
            # Did not enter either
            standup_closing_hour = int(channel.standup_hour) + 1 # Default to one hour until the chance to submit standup closes
            standup_closing_minute = int(channel.standup_minute) # Default to zero minutes
        elif did_not_enter_hours and not did_not_enter_minutes:
            # They only entered minutes
            standup_closing_hour = int(channel.standup_hour)
            standup_closing_minute = int(channel.standup_minute) + int(channel.minutes_delay)
        elif did_not_enter_minutes and not did_not_enter_hours:
            # They only entered hours
            standup_closing_hour = int(channel.standup_hour) + int(channel.hours_delay)
            standup_closing_minute = int(channel.standup_minute)
        else:
            # They entered both
            standup_closing_hour = int(channel.standup_hour) + int(channel.hours_delay)
            standup_closing_minute = int(channel.standup_minute) + int(channel.minutes_delay)
        
        SCHEDULER.add_job(get_timestamp_and_send_email, 'cron', [
                          channel.channel_name, channel.email], day_of_week='mon-sun', hour=standup_closing_hour, minute=standup_closing_minute, id=channel.channel_name + "_sendemail")
        Logger.log("Channel that we set email schedule for: " + channel.channel_name, Logger.info) # Issue 25: eventType: CreateOrUpdateEmailJob
    else:
        Logger.log("Channel " + channel.channel_name + " did not want their standups emailed to them today.", Logger.info) # Issue 25: eventType: CreateOrUpdateEmailJob


# Emailing standup results to chosen email address.
# Timestamp comes in after we make our trigger_standup_call.
# @param channel_name : Name of channel whose standup results we want to email to someone
# @param recipient_email_address : Where to send the standup results to
# @return nothing
def get_timestamp_and_send_email(a_channel_name, recipient_email_address):
    times_up_message = "Submission period for " + a_channel_name + "'s standup has ended. Responses were emailed to " + recipient_email_address
    Logger.log(times_up_message, Logger.info) # Issue 25: eventType: SendStandupEmail

    channel = Channel.query.filter_by(channel_name=a_channel_name).first()
    # Ensure we have a standup report to grab and that this email address is confirmed
    if (channel.timestamp != None and channel.timestamp != "" and channel.email_confirmed):
        # First we need to get all replies to this message:
        standups = slack_client.get_standup_replies_for_message(
            channel.timestamp, channel.channel_name)
        # If we had replies today...
        if (standups != None):
            # Join the list together so it's easier to read
            formatted_standup_message = ''.join(map(str, standups))
            # Then we need to send an email with this information
            email_client.send_email(a_channel_name, recipient_email_address, formatted_standup_message, "Standup Report")
            Logger.log("Sent " + a_channel_name + "'s standup messages, " +
                  formatted_standup_message + ", to " + recipient_email_address, Logger.info) # Issue 25: eventType: SendStandupEmail
            # Finally we need to reset the standup timestamp so we don't get a repeat.
            channel.timestamp = None
            DB.session.commit()
        else:
            # Let them know we had no replies
            message = "Channel " + a_channel_name + " did not have any standup submissions to email today."
            email_client.send_email(a_channel_name, recipient_email_address, message, "No Standup Report For Channel Today")
            Logger.log(message, Logger.info) # Issue 25: eventType: SendStandupEmail
        # Let channel know their results were sent.
        slack_client.send_slack_message(a_channel_name, times_up_message)
    else:
        # Log that it didn't work
        Logger.log("Channel " + a_channel_name +
              " isn't set up to have standup results sent anywhere because they don't have a timestamp in STANDUP_TIMESTAMP_MAP or haven't confirmed their email.", Logger.error) # Issue 25: eventType: SendStandupEmail


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
    hours_delay = DB.Column(DB.Integer)
    minutes_delay = DB.Column(DB.Integer)

    def __init__(self, channel_name, standup_hour, standup_minute, message, email, timestamp, email_confirmed, confirmation_code, hours_delay, minutes_delay):
        self.channel_name = channel_name
        self.standup_hour = standup_hour
        self.standup_minute = standup_minute
        self.message = message
        self.email = email
        self.timestamp = timestamp
        self.email_confirmed = email_confirmed
        self.confirmation_code = confirmation_code
        self.hours_delay = hours_delay
        self.minutes_delay = minutes_delay

    def __repr__(self):
        return '<Channel %r>' % self.channel_name


if __name__ == '__main__':
    app.run(host='0.0.0.0')

# Setting the scheduling
set_schedules()

# Running the scheduling
SCHEDULER.start()

Logger.log("Standup bot was started up and scheduled.", Logger.info) # Issue 25: eventType: Startup
