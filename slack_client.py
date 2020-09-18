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
        replies = result["messages"]
        logger.log(str(replies), "INFO")
        if (replies is not None):
            standup_results = []
            for standup_status in replies:
              logger.log("Raw reply is: " + str(standup_status), "INFO")
              if standup_status["subtype"] != "bot_message":
                # Get username of person who made this reply
                user_result = SLACK_CLIENT.users_info(user=standup_status['user'])
                logger.log("User's info is: " + str(user_result), "INFO")
                name = user_result["user"]["profile"]["real_name"]
                logger.log("Adding standup results for " + name, "INFO")
                standup_response_for_person = name + ": " + standup_status['text'] + "; \n"
                standup_results.append(standup_response_for_person)
            return standup_results
        else:
          logger.log("We got back replies object but it was empty", "INFO")
    else:
        # Log that it didn't work
        logger.log("Tried to retrieve standup results. Could not retrieve standup results for " + channel_name + " due to: " + str(result.error), "ERROR")


# Calls API to get channel ID based on name.
# @param channel_name
# @return channel ID
def get_channel_id_via_name(channel_name):
    channels_list = SLACK_CLIENT.conversations_list(types="public_channel")
    
    logger.log("get_channel_id_via_name " + str(channels_list), "INFO")
    for channel in channels_list["channels"]:
        if channel["name"] == channel_name:
            logger.log("get_channel_id_via_name " + str(channel["name"]) + " == " + channel_name, "INFO")
            return channel["id"]

# Get list of channel names
# @return list of channel names
def get_all_channels():
  channels_list = SLACK_CLIENT.conversations_list(types="public_channel")
  channel_names_list = []
  for channel in channels_list["channels"]:
      channel_names_list.append(channel["name"])
  return channel_names_list