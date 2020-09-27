# Slack Standup Report Bot
### By Christina

## Technologies Used
Python, Flask, wtforms, PostgreSQL

## Setting Standup for Channel
![Setting Your Standup Message](https://raw.githubusercontent.com/cjaiello/standupbot/master/standup-setting-message.gif)

## Submitting Your Report and Email Summary
![Submitting Your Report and Email Summary](https://raw.githubusercontent.com/cjaiello/standupbot/master/standup-submitting-reports-and-emailing.gif)

## Confirming Email Address
To receive an email summary of standup reports, you must confirm your email address:
![Confirming Email Address](https://raw.githubusercontent.com/cjaiello/standupbot/master/standup-confirm-email-address.gif)

And then a screenshot of what this looks like in gmail:
![Screenshot of Gmail Confirmation](https://raw.githubusercontent.com/cjaiello/standupbot/master/confirmation-in-gmail.png)

## Local Development Setup
### Prerequisites
* Install python3:
** Mac: `brew install python3`
*** If you don't have homebrew for the above step, get it here: https://docs.brew.sh/Installation
** Windows: https://phoenixnap.com/kb/how-to-install-python-3-windows
* Install `virtualenv` via `pip3 install virtualenv`

### Setup
* Git clone this directory onto your computer
* Use `cd Slack-Standup-Report-Bot` to change directories into your Slack-Standup-Report-Bot copy
* Run `virtualenv venv --system-site-packages` in that directory
* Run `source venv/bin/activate` to start your virtual environment
* Run `pip3 install -r requirements.txt` to install required dependencies for project
* Run `python -m spacy download en`
* Run `export FLASK_APP=app.py` to set the app
* Run `psql` to run sql
* Run `create database standup` to make your standup database
* Run `\c standup` to connect to the standup database
* Run `CREATE TABLE channel (id SERIAL PRIMARY KEY, channel_name varchar(120), standup_hour int, standup_minute int, message text, email varchar(50), timestamp varchar(50), response_period_in_hours int, email_confirmed boolean, confirmation_code varchar(120), hours_delay int, minutes_delay int);` to create your table you'll need for this app
* Run `\q` to quit psql
* Run `export DATABASE_URL="postgresql:///standup"` to set an environment variable that points to your newly-created database
* Run `flask run` to start the app
