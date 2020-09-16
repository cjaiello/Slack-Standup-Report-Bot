from slackclient import SlackClient
import util
import os
import requests

SLACK_CLIENT = SlackClient(os.environ['SLACK_BOT_CHANNEL_URL'])

# Will send @param message to @param channel_name
def call_slack_messaging_api(channel_name, message):
  text = {"text" : message}
  response = requests.post(os.environ['SLACK_BOT_CHANNEL_URL'], data = text)
  print(util.create_logging_label() + "Result of call to slack was: " + response.text + "\n" + response.json)

# Will fetch the standup messages for a channel
# @param timestamp : A channel's standup message's timestamp (acquired via API)
# @return Standup messages in JSON format
# TODO: DOES THIS STILL WORK?
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
        print(util.create_logging_label() + "Tried to retrieve standup results. Could not retrieve standup results for " + channel_name + " due to: " + str(result.error))


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
    print(util.create_logging_label() + "Adding standup results for " + user_result.get("user").get("real_name"))
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
