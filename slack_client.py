import util
import os
import slack
import logger

SLACK_CLIENT = slack.WebClient(os.environ["SLACK_BOT_TOKEN"], timeout=30)

# Will send @param message to @param channel_name
def send_standup_message(channel_name, message):
  response = SLACK_CLIENT.chat_postMessage(
      channel=str(channel_name),
      text= ("Please reply here with your standup status!" if (message == None) else message),
      username="Standup Bot",
      icon_emoji=":memo:"
  )
  logger.log("send_standup_message response code: " + str(response.status_code), "INFO")
  for item in response.data.items():
    logger.log("send_standup_message response[" + str(item[0]) + "]: " + str(item[1]), "INFO")
  return response

# Will send confirmation message to @param channel_name
def send_confirmation_message(channel_name, message):
  response = SLACK_CLIENT.chat_postMessage(
      channel=str(channel_name),
      text= ("Please reply here with your standup status!" if (message == None) else  message),
      username="Standup Bot",
      icon_emoji=":memo:"
  )
  logger.log("send_confirmation_message response code: " + str(response.status_code), "INFO")
  for item in response.data.items():
    logger.log("send_confirmation_message response[" + str(item[0]) + "]: " + str(item[1]), "INFO")
  return response.status_code

# Will fetch the standup messages for a channel
# @param timestamp : A channel's standup message's timestamp (acquired via API)
# @return Standup messages in JSON format
# TODO: Make sure this still works
def get_standup_replies_for_message(timestamp, channel_name):
    channel_id = get_channel_id_via_name(channel_name)

    # https://api.slack.com/methods/conversations.history
    logger.log(str({'channel': channel_id, 'latest': timestamp}), "INFO")
    result = SLACK_CLIENT.conversations_replies(
      channel=channel_id,
      ts=timestamp,
      latest='now',
      inclusive=True,
      count=1
    )
    logger.log(str(result), "INFO")
    # Need to ensure that API call worked
    if (result["ok"]):
        logger.log("Successfully got standup replies for message", "INFO")
        # Only do the following if we actually got replies
        replies = result.get("messages")[0].get("replies")
        logger.log(str(replies), "INFO")
        if (replies is not None):
            standup_results = []
            for standup_status in replies:
                # Add to our list of standup messages
                standup_results.append(retrieve_standup_reply_info(channel_id, standup_status.get("ts")))
            return standup_results
        else:
          logger.log("We got back replies object but it was empty", "INFO")
    else:
        # Log that it didn't work
        logger.log("Tried to retrieve standup results. Could not retrieve standup results for " + channel_name + " due to: " + str(result.error), "ERROR")


# Getting detailed info about this reply, since the initial call
# to the API only gives us the user's ID# and the message's timestamp (ts)
# @param channel_id: ID of the channel whom we're reporting for
# @param standup_status_timestamp: Timestamp for this message
# TODO: Make sure this still works
def retrieve_standup_reply_info(channel_id, standup_status_timestamp):
    reply_result = SLACK_CLIENT.conversations_history(
      channel=channel_id,
      latest=standup_status_timestamp,
      inclusive=True,
      count=1
    )
    # Get username of person who made this reply
    user_result = SLACK_CLIENT.users_info(
      user=reply_result.get("messages")[0].get("user")
    )
    logger.log("Adding standup results for " + user_result.get("user").get("real_name"), "INFO")
    return user_result.get("user").get("real_name") + ": " + reply_result.get("messages")[0].get("text") + "; \n"


# Calls API to get channel ID based on name.
# @param channel_name
# @return channel ID
def get_channel_id_via_name(channel_name):
    channels_list = SLACK_CLIENT.conversations_list(types="public_channel")
    
    logger.log("get_channel_id_via_name " + str(channels_list), "INFO")
    for channel in channels_list.get("channels"):
        if channel.get("name") == channel_name:
            logger.log("get_channel_id_via_name " + str(channel.get("name")) + " == " + channel_name, "INFO")
            return channel.get("id")

# Get list of channel names
# @return list of channel names
def get_all_channels():
  channels_list = SLACK_CLIENT.conversations_list(types="public_channel")
  channel_names_list = []
  for channel in channels_list.get("channels"):
      channel_names_list.append(channel.get("name"))
  return channel_names_list