# Standup Bot by Christina Aiello, 2017-2020
import smtplib
import os
import html
from logger import Logger

# Sends an email via our gmail account to the chosen email address
# @param channel_name: The channel that we are sending updates about
# @param recipient_email_address: The email address receiving the updates
# @param email_content: The content of the email body
# @param email_subject: The subject of the email
def send_email(channel_name, recipient_email_address, email_content, email_subject):
    event_type = "SendEmail"
    Logger.log("Email info: " + str(channel_name) + " | " + str(recipient_email_address) + " | " + email_content, Logger.info, event_type)
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.login(os.environ['USERNAME'], os.environ['PASSWORD'])
    Logger.log("Username is " + os.environ['USERNAME'], Logger.info, event_type)
    message = 'Subject: {}\n\n{}'.format("#" + channel_name + " " + email_subject, html.unescape(email_content))
    Logger.log(message, Logger.info, event_type)
    server.sendmail(os.environ['USERNAME'], recipient_email_address, message)
    server.quit()