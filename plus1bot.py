from telegram.ext import MessageHandler, Filters, StringRegexHandler, PicklePersistence
from telegram.ext import CommandHandler
from telegram.ext import Updater
import logging
import re
import requests
import base64
import json


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


url_finder = re.compile(
    "/(?:(?:https?|ftp|file):\/\/|www\.|ftp\.)(?:\([-A-Z0-9+&@#\/%=~_|$?!:,.]*\)|[-A-Z0-9+&@#\/%=~_|$?!:,.])*(?:\([-A-Z0-9+&@#\/%=~_|$?!:,.]*\)|[A-Z0-9+&@#\/%=~_|$])/igm")


def add_to_dict_key(dict_to_update, key, value):
    dict_to_update.setdefault(key, 0)
    dict_to_update[key] += value


def update_vote_data(data, song_id, size_of_vote):
    if size_of_vote >= 0:
        sign = "+"
    else:
        sign = "-"

    data.setdefault("{}1_given".format(sign), {})
    data.setdefault("{}x_given".format(sign), {})

    add_to_dict_key(data["{}1_given".format(sign)], song_id, 1)
    add_to_dict_key(data["{}x_given".format(sign)], song_id, size_of_vote)


def start(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Hi i am the +1 spotify bot try replying to a spotify link with +1.\n  You can also try /help if you are scared and confused")


def echo(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=update.message.text)


def get_album_info_from_url(shared_url):
    track_id = shared_url.split("?")[0].split("/")[-1]
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
    elif "playlist":
        link_type = "playlists"
    else:
        logging.warning("Can't find album/track in url")

    spotify_data = request_from_spotify(
        'https://api.spotify.com/v1/{}/{}'.format(link_type, track_id), spotify_token)

    try:
        if spotify_data["error"]["message"] == "The access token expired":
            spotify_token = get_new_token()
    except KeyError:
        pass
    else:
        spotify_data = request_from_spotify(
            'https://api.spotify.com/v1/{}/{}'.format(link_type, track_id), spotify_token)
    if "album" in shared_url or "track" in shared_url:
        return spotify_data['name'], spotify_data['artists'][0]['name']
    elif "playlist" in shared_url:
        return spotify_data['name'], "playlist"


def parse_message(update, context):
    url_match = find_all_urls_in_message(update.message.text)
    if url_match:
        url_found(update, context, url_match)

    number_finder = re.compile('[+-]\d*')
    number_match = number_finder.match(update.message.text)
    if number_match:
        try:
            number = int(number_match.group())
        except ValueError:
            pass
        else:
            count_plus1(update, context, number)
            pass


def find_all_urls_in_message(text):
    url_match = re.findall(
        '(?:(?:https?|ftp):\/\/)?[\w/\-?=%.]+\.[\w/\-?=%.]+', text)
    return url_match


def url_found(update, context, url_groups):
    for url in url_groups:
        context.chat_data.setdefault("all_urls_shared", [])
        context.chat_data["all_urls_shared"].append(url)

def respond_to_message(context,update, text):
    if not silent:
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)  


def count_plus1(update, context, number):
    for url in find_all_urls_in_message(update.message.reply_to_message.text):
        if url.startswith("https://open.spotify.com"):
            song_name, artist = get_album_info_from_url(url)

            text = "{0!s} has given {1:+d} to {2!s} by {3!s}".format(
                update.effective_user.first_name, number, song_name, artist)
            song_id = "{}:{}".format(song_name, artist)
            update_vote_data(context.user_data, song_id, number)
            update_vote_data(context.chat_data, song_id, number)

            respond_to_message(context,update,text)


def helpfunc(update, context):
    text = "You can call all of these functions \n Up/Down voting is done by replying to spotify links"
    for command in commands:
        text += "/{}: {}\n".format(command["command"], command["helpstring"])

    context.bot.send_message(chat_id=update.effective_chat.id, text=text)


def report_list(text, dict_data, asending=True, max_length=10):
    try:
        sorted_dict = sorted(
            dict_data.items(), key=lambda item: item[1])
    except KeyError:
        text = "No scores yet!!"
    else:
        if asending:
            sorted_dict.reverse()
        for i, (song, score) in enumerate(sorted_dict[:max_length]):
            text += "\t{0}. {1} \t({2}) \n".format(i,
                                                   song, score)
    return text


def upvotes(update, context):
    text = "Upvotes \n\n"
    try:
        text = report_list(
            text, context.chat_data["+1_given"], asending=True)
    except KeyError:
        text = "No upvotes found"
    context.bot.send_message(chat_id=update.effective_chat.id, text=text)


def my_upvotes(update, context):
    text = "Upvotes \n\n"
    try:
        text = report_list(
            text, context.user_data["+1_given"], asending=True)
    except KeyError:
        text = "No upvotes found"
    context.bot.send_message(chat_id=update.effective_chat.id, text=text)


def my_downvotes(update, context):
    text = "Downvotes \n\n"
    try:
        text = report_list(
            text, context.user_data["-1_given"], asending=False)
    except KeyError:
        text = "No downvotes found"
    context.bot.send_message(chat_id=update.effective_chat.id, text=text)


def downvotes(update, context):
    text = "Downvotes \n\n"
    try:
        text = report_list(
            text, context.chat_data["-1_given"], asending=False)
    except KeyError:
        text = "No downvotes found"
    context.bot.send_message(chat_id=update.effective_chat.id, text=text)


def my_stats(update, context):
    text = "My Stats \n"
    try:
        text += "Total Upvotes given is : {}\n".format(
            sum(context.user_data["+x_given"].values()))
        text += "\nMy top 5 most loved\n"
        text = report_list(text, context.user_data["+x_given"], max_length=5)
    except KeyError:
        pass

    try:
        text += "\nTotal Downvotes given is : {}\n".format(
            sum(context.user_data["-x_given"].values()))
        text += "\nMy top 5 most hated\n"
        text = report_list(text, context.user_data["-x_given"], max_length=5)
    except KeyError:
        pass

    context.bot.send_message(chat_id=update.effective_chat.id, text=text)


def get_new_token():

    auth_str = '{0}:{1}'.format(creds["client_id"], creds["client_secret"])
    b64_auth_str = base64.urlsafe_b64encode(auth_str.encode()).decode()

    response = requests.post('https://accounts.spotify.com/api/token',
                             headers={
                                 'Authorization': 'Basic {0}'.format(b64_auth_str)},
                             data={
                                 'grant_type': 'client_credentials'
                             })
    return json.loads(response.text)["access_token"]


def request_from_spotify(request, token):
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer {}'.format(token),
    }

    response = requests.get(request,  headers=headers)
    spotify_data = json.loads(response.text)

    response = requests.get(request,  headers=headers)
    spotify_data = json.loads(response.text)

    return spotify_data

def shutup(update, context):
    silent = True

def shout(update,context):
    silent = False

if __name__ == "__main__":
    silent = False

    with open("secrets.json", 'r') as f:
        creds = json.load(f)
    commands = [
        {"command": "start", "function": start,
            "helpstring": "The welcome function"},
        {"command": "help", "function": helpfunc,
            "helpstring": "The function you just called"},
        {"command": "upvotes", "function": upvotes,
            "helpstring": "Most upvoted of all time"},
        {"command": "downvotes", "function": downvotes,
         "helpstring": "Most downvoted of all time"},
        {"command": "myupvotes", "function": my_upvotes,
         "helpstring": "Most upvoted of all time"},
        {"command": "mydownvotes", "function": my_downvotes,
         "helpstring": "Most downvoted of all time"},
        {"command": "mystats", "function": my_stats,
         "helpstring": "Info on your stats"},
         {"command": "shutup", "function": shutup,
         "helpstring": "Bot will no longer respond when you +1 will still count though."},
         {"command": "beloud", "function": shout,
         "helpstring": "Bot will respond to every message not just commands"},
    ]

    number_finder = re.compile('[+-]\d*')
    persistence = PicklePersistence(filename="botdata")
    updater = Updater(
        token=creds["telegram_token"], use_context=True, persistence=persistence)
    dispatcher = updater.dispatcher
    # should regex here to find the count func
    count_handler = MessageHandler(Filters.all, parse_message)

    for command in commands:
        dispatcher.add_handler(CommandHandler(
            command['command'], command['function']))

    dispatcher.add_handler(count_handler)

    updater.start_polling()
    updater.idle()
