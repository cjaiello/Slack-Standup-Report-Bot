# Standup Bot by Christina Aiello, 2017
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
app = Flask(__name__)
DB = SQLAlchemy(app)

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
