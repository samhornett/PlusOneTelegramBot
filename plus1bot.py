from telegram.ext import MessageHandler, Filters, StringRegexHandler, PicklePersistence
from telegram.ext import CommandHandler
from telegram.ext import Updater
import logging
import re
import secrets
import requests

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def start(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")


def echo(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=update.message.text)


def get_album_info_from_url(shared_url):
    track_id = shared_url.split("?")[0].split("/")[-1]
    print(track_id)
    with open("secrets.json", 'r') as f:
        spotify_token = json.load(f)["spotify_token"]


    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer {}'.format(spotify_token),
    }

    if "album" in shared_url:
        link_type = "albums"
    elif "track" in shared_url:
        link_type = "tracks"
    else:
        logging.warning("Can't find album/track in url")

    response = requests.get(
        'https://api.spotify.com/v1/{}/{}'.format(link_type, track_id),  headers=headers)
    spotify_data = json.loads(response.text)

    return spotify_data['name'], spotify_data['artists'][0]['name']


def count_plus1(update, context):
    context.user_data .setdefault("-1_given", 0)
    context.user_data.setdefault("+1_given", 0)
    context.user_data .setdefault("neg_total_given", 0)
    context.user_data.setdefault("pos_total_given", 0)

    context.chat_data.setdefault("Songs_recommended", {})
    context.chat_data.setdefault("Songs_recommended_total", {})

    number_finder = re.compile('[+-]\d*')
    m = number_finder.match(update.message.text)
    if m:
        try:
            number = int(m.group())
        except ValueError:
            pass
        else:
            if number > 0:
                context.user_data["+1_given"] += 1
                context.user_data["pos_total_given"] += number
            if number < 0:
                context.user_data["-1_given"] += 1
                context.user_data["neg_total_given"] += number

            if update.message.reply_to_message:
                if len(update.message.reply_to_message.entities) > 0:
                    if update.message.reply_to_message.entities[0]["type"] == "url":
                        url = update.message.reply_to_message.text
                        if url.startswith("https://open.spotify.com"):
                            song_name, artist = get_album_info_from_url(url)

                            text = "{0!s} has given {1:+d} to {2!s} by {3!s}".format(
                                update.effective_user.first_name, number, song_name, artist)
                            context.chat_data["Songs_recommended"].setdefault(
                                "{} by {}".format(song_name, artist), 0)
                            context.chat_data["Songs_recommended"]["{} by {}".format(
                                song_name, artist)] += 1
                            context.chat_data["Songs_recommended_total"].setdefault(
                                "{} by {}".format(song_name, artist), 0)
                            context.chat_data["Songs_recommended_total"]["{} by {}".format(
                                song_name, artist)] += number

                else:
                    text = "{0!s} has given {1:+d} to {2!s}".format(
                        update.effective_user.first_name, number, update.message.reply_to_message.from_user.first_name)
            else:
                text = "{0!s} has given {1:+d} ".format(
                    update.effective_user.first_name, number)
            context.bot.send_message(
                chat_id=update.effective_chat.id, text=text)


def helpfunc(update, context):
    text = "You can call all of these functions \n"
    for command in commands:
        text += "/{}: {}\n".format(command["command"], command["helpstring"])

    context.bot.send_message(chat_id=update.effective_chat.id, text=text)


def songs(update, context):
    text = "Most upvoted urls \n"
    try:
        sorted_dict = {k: v for k, v in sorted(
            context.chat_data["Songs_recommended"].items(), key=lambda item: item[1])}
    except KeyError:
        text = "No scores yet!!"
    else:
        for song, score in sorted_dict.items():
            text += "{} got {} upvotes for a total of {} \n".format(
                song, score, context.chat_data["Songs_recommended_total"][song])

    context.bot.send_message(chat_id=update.effective_chat.id, text=text)


if __name__ == "__main__":
    import json
    commands = [
        {"command": "start", "function": start,
            "helpstring": "The welcome function"},
        {"command": "help", "function": helpfunc,
            "helpstring": "The function you just called"},
        {"command": "songs", "function": songs,
            "helpstring": "Current leaderboard for songs"},


    ]

    with open("secrets.json", 'r') as f:
        token = json.load(f)["telegram_token"]

    number_finder = re.compile('[+-]\d*')
    persistence = PicklePersistence(filename="botdata")
    updater = Updater(
        token=token, use_context=True, persistence=persistence)
    dispatcher = updater.dispatcher
    count_handler = MessageHandler(Filters.all, count_plus1)

    for command in commands:
        dispatcher.add_handler(CommandHandler(
            command['command'], command['function']))

    dispatcher.add_handler(count_handler)

    updater.start_polling()
