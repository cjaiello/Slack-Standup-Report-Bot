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
* python3, specfically Python 3.8 (Mac: `brew install python3`, and if you don't have homebrew for the above step, get it here: https://docs.brew.sh/Installation; Windows: https://phoenixnap.com/kb/how-to-install-python-3-windows)
* `virtualenv`, installed via `pip3 install virtualenv` for Mac and Linux or `py -m pip install --user virtualenv` for Windows

### Setup
* Fork this repository (https://docs.github.com/en/free-pro-team@latest/github/getting-started-with-github/fork-a-repo)
* Run `git clone` to clone this project onto your computer (https://docs.github.com/en/free-pro-team@latest/github/getting-started-with-github/fork-a-repo or https://git-scm.com/book/en/v2/Git-Basics-Getting-a-Git-Repository)
* Use `cd Slack-Standup-Report-Bot` to change directories into your Slack-Standup-Report-Bot copy
* Run `./build-mac-and-linux.sh` (MacOS or Linux) or `./build-winows.sh` (Windows) to run my build script to set everything up for you. (If it won't run, do `chmod +x ./build-mac-and-linux.sh` if Mac/Linux or `chmod +x build-winows.sh` if Windows and then run the script again. +x will let it be executed.)
  * If you're wondering what the script does, these are each of its parts (and if you don't care, that's fine too!):
    * Running `virtualenv -p python3.8 myenv` to create a virtual environment
    * Running `source myenv/bin/activate` to start your virtual environment
    * Running `pip3 install -r requirements.txt` to install required dependencies for project
    * Running `python -m spacy download en`
    * Running `export FLASK_APP=app.py` to set the app
    * Running `psql` to run sql
    * Running `create database standup` to make your standup database
    * Running `CREATE TABLE channel (id SERIAL PRIMARY KEY, channel_name varchar(120), standup_hour int, standup_minute int, message text, email varchar(50), timestamp varchar(50), response_period_in_hours int, email_confirmed boolean, confirmation_code varchar(120), hours_delay int, minutes_delay int);` to create your table you'll need for this app
    * Running `export DATABASE_URL="postgresql:///standup"` to set an environment variable that points to your newly-created database
    * Running `gunicorn --bind 0.0.0.0:5000 wsgi:app;` to start the app
* Go to http://127.0.0.1:5000/ to see your app running
* To exit `myenv`, your virtual environment, just type `deactivate` and hit enter




## Setup to Work Locally but Run App on Heroku and Interact with Slack
Each time you make changes, you'll push to Github, which we'll set up to trigger an automatic deploy to Heroku. Your bot can then use your new changes.

### Make Heroku app
* Install the Heroku CLI (command line interface) https://devcenter.heroku.com/articles/heroku-cli
* Go to https://dashboard.heroku.com/apps (register if you haven't)
* Click `New` and then `Create New App`
* Give it a name and click `Create`
* You will be dropped onto the `Deploy` tab. Note your app name and how to access your app via web browser:
![Your App Name](https://github.com/cjaiello/Slack-Karma-Bot/blob/master/static/this-is-your-app-name.png)
* In the `Deployment method` section, click `GitHub` `Connect to Github`
![Connect to Github](https://github.com/cjaiello/Slack-Karma-Bot/blob/master/static/deployment-method-github.png)
* Choose your repository
* Click `Enable Automatic Deploys`. Now, anytime you push to Github, your code will be automatically deployed to Heroku!
* Go to the Resources tab
* In the `Add-Ons` section, type in `Heroku Postgres` and install the `Hobby Dev - Free` version
![Install Postgres](https://github.com/cjaiello/Slack-Karma-Bot/blob/master/static/database-heroku-install-postgres.png)
* Go back to the `Settings` tab and click `Reveal config vars` again
* The new `DATABASE_URL` config var (environment variable) has been added for you! Now when you access `os.environ["DATABASE_URL"]` in the Slack Standup Bot app code, the application will pull in the value of that new `DATABASE_URL`
![Postgres](https://github.com/cjaiello/Slack-Karma-Bot/blob/master/static/config-vars-database-url.png)


### Make Slack Workspace and Slack App+Bot
* Make a Slack workspace (They're free, don't worry!) at https://slack.com/create or I can invite you to a test Slack workspace I set up for this Slack bot and my standup Slack bot
* Go to `https://api.slack.com/apps`
* Make your app and attach it to your workspace you just made
![Create Slack App](https://github.com/cjaiello/Slack-Karma-Bot/blob/master/static/create-slack-app.png)
* On the Basic Information page, go to `Permissions`
* Scroll down to `Bot Token Scopes`
* Add: `channels:history`, `channels:join`, `channels:read`, `chat:write`, `chat:write.customize`, `chat:write.public`, `groups:history`, `incoming-webhook`, `users.profile:read`, `users:read`
* Now scroll up and click `Install App to Workspace`
![Install App to Workspace](https://github.com/cjaiello/Slack-Karma-Bot/blob/master/static/permissions-tokens-access-token-install-to-workspace.png)
* You now have a bot token! 
![Bot Token](https://github.com/cjaiello/Slack-Karma-Bot/blob/master/static/permissions-tokens-access-token-to-copy.png)
* On the Heroku Settings tab `https://dashboard.heroku.com/apps/christinastest/settings` (or whatever your URL is, which will have something other than `christinastest` and will instead have your app's name in it), go to `Reveal config vars` again and add the Slackbot token: `SLACK_BOT_TOKEN` and value is whatever your value is
![Slackbot Token](https://github.com/cjaiello/Slack-Karma-Bot/blob/master/static/config-vars-slack-bot-token.png)

### Final Setup Steps
* Go to the #general channel in Slack and tag the bot, example: 
```
your-username  9:56 PM
@Name Of Your App
```
* After tagging the bot, you'll be asked to invite it to the channel. Invite it.
* Go back to the Heroku `Resources` tab (Ex: https://dashboard.heroku.com/apps/christinastest/resources)
* Click on your database
* At the top of the page you're brought to, copy the name (Example: `postgresql-cubed-27245`)
* Open up a new terminal and run `heroku pg:psql postgresql-cubed-27245 --app christinastest` in any directory, where `postgresql-cubed-27245` is the name of your database and `christinastest` is the name of your app
![Get Database Name](https://github.com/cjaiello/Slack-Karma-Bot/blob/master/static/get-database-name.png)
* Now that you're connected to your database, run `CREATE TABLE channel (id SERIAL PRIMARY KEY, channel_name varchar(120), standup_hour int, standup_minute int, message text, email varchar(50), timestamp varchar(50), response_period_in_hours int, email_confirmed boolean, confirmation_code varchar(120), hours_delay int, minutes_delay int);` to create your table
* That's it!

### Debugging
* If you're having issues and need to debug, run `heroku logs --tail --app christinastest` in a terminal window (in any directory), where `christinastest` is the name of your app on heroku. To quit, type `\q`
