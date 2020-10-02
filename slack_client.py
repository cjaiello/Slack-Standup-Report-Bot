# Standup Bot by Christina Aiello, 2017-2020
import util
import os
import slack
from logger import Logger

if 'SLACK_BOT_TOKEN' in os.environ:
  SLACK_CLIENT = slack.WebClient(os.environ["SLACK_BOT_TOKEN"], timeout=30)
else:
  SLACK_CLIENT = None

# Will send @param message to @param channel_name
def send_standup_message(channel_name, message):
  event_type = "SendStandupMessage"
  if SLACK_CLIENT:
    response = SLACK_CLIENT.chat_postMessage(
        channel=str(channel_name),
        text= ("Please reply here with your standup status!" if (message == None) else message),
        username="Standup Bot",
        icon_emoji=":memo:"
    )
  Logger.log("send_standup_message response code: " + str(response.status_code), Logger.info, event_type)
  for item in response.data.items():
    Logger.log("send_standup_message response[" + str(item[0]) + "]: " + str(item[1]), Logger.info, event_type)
  return response


# Will send confirmation message to @param channel_name
def send_confirmation_message(channel_name, message):
  event_type = "SendConfirmationMessage"
  response = send_slack_message(channel_name, "Please reply here with your standup status!" if (message == None) else  message)
  if response:
    Logger.log("send_confirmation_message response code: " + str(response.status_code), Logger.info, event_type)
    for item in response.data.items():
      Logger.log("send_confirmation_message response[" + str(item[0]) + "]: " + str(item[1]), Logger.info, event_type)
    return response.status_code
  else:
    return None

# Sends given slack message to given slack channel
def send_slack_message(channel_name, message):
  if SLACK_CLIENT:
    response = SLACK_CLIENT.chat_postMessage(
        channel=str(channel_name),
        text= (message),
        username="Standup Bot",
        icon_emoji=":memo:"
    )
  else:
    response = None
  return response

# Will fetch the standup messages for a channel
# @param timestamp : A channel's standup message's timestamp (acquired via API)
# @return Standup messages in JSON format
# TODO: Make sure this still works
def get_standup_replies_for_message(timestamp, channel_name):
  event_type = "GetStandupReports"
  if SLACK_CLIENT:
    channel_id = get_channel_id_via_name(channel_name)

    # https://api.slack.com/methods/conversations.history
    Logger.log(str({'channel': channel_id, 'latest': timestamp}), Logger.info, event_type)
    result = SLACK_CLIENT.conversations_replies(
      channel=channel_id,
      ts=timestamp,
      latest='now',
      inclusive=True,
      count=1
    )
    Logger.log(str(result), Logger.info)
    # Need to ensure that API call worked
    if (result["ok"]):
        Logger.log("Successfully got standup replies for message", Logger.info, event_type)
        # Only do the following if we actually got replies
        replies = result["messages"]
        Logger.log(str(replies), Logger.info, event_type)
        if (replies is not None):
            standup_results = []
            for standup_status in replies:
              Logger.log("Raw reply is: " + str(standup_status), Logger.info, event_type)
              if ("subtype" not in standup_status):
                # Get username of person who made this reply
                user_result = SLACK_CLIENT.users_info(user=standup_status['user'])
                name = user_result["user"]["profile"]["real_name"]
                Logger.log("Adding standup results for " + name, Logger.info, event_type)
                standup_response_for_person = name + ": " + standup_status['text'] + "\n\n\n"
                standup_results.append(standup_response_for_person)
            Logger.log("Final standup results: " + str(standup_results), Logger.info, event_type)
            return standup_results
        else:
          Logger.log("We got back replies object but it was empty", Logger.info, event_type)
    else:
        # Log that it didn't work
        Logger.log("Tried to retrieve standup results. Could not retrieve standup results for " + channel_name + " due to: " + str(result.error), Logger.error, event_type)
  else:
    return None

# Calls API to get channel ID based on name.
# @param channel_name
# @return channel ID
def get_channel_id_via_name(channel_name):
  event_type = "GetChannelInfo"
  if SLACK_CLIENT:
    channels_list = SLACK_CLIENT.conversations_list(types="public_channel")
    Logger.log("get_channel_id_via_name " + str(channels_list), Logger.info, event_type)
    for channel in channels_list["channels"]:
        if channel["name"] == channel_name:
            Logger.log("get_channel_id_via_name " + str(channel["name"]) + " == " + channel_name, Logger.info, event_type)
            return channel["id"]
  else:
    return None

# Get list of channel names
# @return list of channel names
def get_all_channels():
  if SLACK_CLIENT:
    channels_list = SLACK_CLIENT.conversations_list(types="public_channel")
    channel_names_list = []
    for channel in channels_list["channels"]:
        channel_names_list.append(channel["name"])
    Logger.log("Channel list is: " + str(channel_names_list), Logger.info, "GetChannelList")
  else:
    channel_names_list = ["Dummy Name 1", "Dummy Name 2"]
  return channel_names_list