py -m pip install --user virtualenv;
virtualenv -p c:\Python38\python.exe myenv;
.\myenv\Scripts\activate;
pip3 install -r requirements.txt;
python3 -m spacy download en;
export FLASK_APP=app.py;
psql -U postgres -c "create database standup";
psql -U postgres -d standup <<EOF
CREATE TABLE channel (id SERIAL PRIMARY KEY, channel_name varchar(120), standup_hour int, standup_minute int, message text, email varchar(50), timestamp varchar(50), response_period_in_hours int, email_confirmed boolean, confirmation_code varchar(120), hours_delay int, minutes_delay int);
EOF
export DATABASE_URL="postgresql:///standup";
gunicorn --bind 0.0.0.0:5000 wsgi:app;
