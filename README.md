# Slack Standup Report Bot
### By Christina

## Technologies Used
Python, Flask, PostgreSQL, Gunicorn

## Setting Standup for Channel
![Setting Your Standup Message](https://raw.githubusercontent.com/cjaiello/standupbot/master/static/standup-setting-message.gif)

## Submitting Your Report and Email Summary
![Submitting Your Report and Email Summary](https://raw.githubusercontent.com/cjaiello/standupbot/master/static/standup-submitting-reports-and-emailing.gif)

## Confirming Email Address
To receive an email summary of standup reports, you must confirm your email address:
![Confirming Email Address](https://raw.githubusercontent.com/cjaiello/standupbot/master/static/standup-confirm-email-address.gif)

And then a screenshot of what this looks like in gmail:
![Screenshot of Gmail Confirmation](https://raw.githubusercontent.com/cjaiello/standupbot/master/static/confirmation-in-gmail.png)

## Local Development Setup
**(Does not have Slack integration but allows you to still view the standup form and submit it to the database, letting you see what you need when making all HTML, all CSS, and some Python changes)**

### Prerequisites
* Git (https://git-scm.com/downloads)
* python3, specfically Python 3.8 or higher (Mac: `brew install python3`, and if you don't have homebrew for the above step, get it here: https://docs.brew.sh/Installation; Windows: https://phoenixnap.com/kb/how-to-install-python-3-windows)
* `virtualenv`, installed via `pip3 install virtualenv` for Mac and Linux or `py -m pip install --user virtualenv` for Windows

### Setup
* Fork this repository (https://docs.github.com/en/free-pro-team@latest/github/getting-started-with-github/fork-a-repo)
* Run `git clone` to clone this project onto your computer (https://docs.github.com/en/free-pro-team@latest/github/getting-started-with-github/fork-a-repo or https://git-scm.com/book/en/v2/Git-Basics-Getting-a-Git-Repository)
* Use `cd Slack-Standup-Report-Bot` to change directories into your Slack-Standup-Report-Bot copy
* Run `./build-mac-and-linux` (MacOS or Linux) or `./build-winows` (Windows) to run my build script to set everything up for you. (If it won't run, do `chmod +x build` and then `./build`)
  * If you're wondering what the script does, these are each of its parts:
  * Run `virtualenv -p python3.8 myenv` in that directory
  * Run `source myenv/bin/activate` to start your virtual environment
  * Run `pip3 install -r requirements.txt` to install required dependencies for project
  * Run `python -m spacy download en`
  * Run `export FLASK_APP=app.py` to set the app
  * Run `psql` to run sql
  * Run `create database standup` to make your standup database
  * Run `CREATE TABLE channel (id SERIAL PRIMARY KEY, channel_name varchar(120), standup_hour int, standup_minute int, message text, email varchar(50), timestamp varchar(50), response_period_in_hours int, email_confirmed boolean, confirmation_code varchar(120), hours_delay int, minutes_delay int);` to create your table you'll need for this app
  * Run `export DATABASE_URL="postgresql:///standup"` to set an environment variable that points to your newly-created database
  * Run `gunicorn --bind 0.0.0.0:5000 wsgi:app;` to start the app
* Go to http://127.0.0.1:5000/ to see your app running
* To exit `venv`, your virtual environment, just type `deactivate` and hit enter
