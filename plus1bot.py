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


class TelegramBot:

    def __init__(self):
        self.silent = True

        with open("secrets.json", 'r') as f:
            self.creds = json.load(f)

        self.commands = [
            {"command": "start", "function": self.start,
                "helpstring": "The welcome function"},
            {"command": "help", "function": self.helpfunc,
                "helpstring": "The function you just called"},
            {"command": "upvotes", "function": self.upvotes,
                "helpstring": "Most upvoted of all time"},
            {"command": "downvotes", "function": self.downvotes,
             "helpstring": "Most downvoted of all time"},
            {"command": "myupvotes", "function": self.my_upvotes,
             "helpstring": "Most upvoted of all time"},
            {"command": "mydownvotes", "function": self.my_downvotes,
             "helpstring": "Most downvoted of all time"},
            {"command": "mystats", "function": self.my_stats,
             "helpstring": "Info on your stats"},
            {"command": "shutup", "function": self.shutup,
             "helpstring": "Bot will no longer respond when you +1 will still count though."},
            {"command": "beloud", "function": self.shout,
             "helpstring": "Bot will respond to every message not just commands"},
        ]

        self.refresh_token()
        persistence = PicklePersistence(filename="botdata")
        self.updater = Updater(
            token=self.creds["telegram_token"], use_context=True, persistence=persistence)
        self.dispatcher = self.updater.dispatcher
        # should regex here to find the count func
        count_handler = MessageHandler(Filters.all, self.parse_message)

        for command in self.commands:
            self.dispatcher.add_handler(CommandHandler(
                command['command'], command['function']))

        self.dispatcher.add_handler(
            CommandHandler("sandwitch", self.sandwitch))
        self.dispatcher.add_handler(CommandHandler(
            "sudosandwitch", self.sudosandwitch))

        self.dispatcher.add_handler(count_handler)

    def add_to_dict_key(self, dict_to_update, key, value):
        dict_to_update.setdefault(key, 0)
        dict_to_update[key] += value

    def update_vote_data(self, data, song_id, size_of_vote):
        if size_of_vote >= 0:
            sign = "+"
        else:
            sign = "-"

        data.setdefault("{}1_given".format(sign), {})
        data.setdefault("{}x_given".format(sign), {})

        self.add_to_dict_key(data["{}1_given".format(sign)], song_id, 1)
        self.add_to_dict_key(
            data["{}x_given".format(sign)], song_id, size_of_vote)

    def start(self, update, context):
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Hi i am the +1 spotify bot try replying to a spotify link with +1.\n  You can also try /help if you are scared and confused")

    def echo(self, update, context):
        context.bot.send_message(
            chat_id=update.effective_chat.id, text=update.message.text)

    def sandwitch(self, update, context):
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Get yourself a sandwitch!")

    def sudosandwitch(self, update, context):
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="What can I get you?")

    def get_album_info_from_url(self, shared_url):
        track_id = shared_url.split("?")[0].split("/")[-1]

        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {}'.format(self.spotify_token),
        }

        if "album" in shared_url:
            link_type = "albums"
        elif "track" in shared_url:
            link_type = "tracks"
        elif "playlist":
            link_type = "playlists"
        else:
            logging.warning("Can't find album/track in url")

        spotify_data = self.request_from_spotify(
            'https://api.spotify.com/v1/{}/{}'.format(link_type, track_id))

        if "album" in shared_url or "track" in shared_url:
            return spotify_data['name'], spotify_data['artists'][0]['name']
        elif "playlist" in shared_url:
            return spotify_data['name'], " (playlist)"

    def add_to_playlist(self, track_id, playlist_id="4TgBbmOB7T1c5Dso2dpgny"):
        params = (
            ('position', '0'),
            ('uris', track_id),
        )

        response = self.request_from_spotify(
            'https://api.spotify.com/v1/playlists/{}/tracks'.format(playlist_id), params=params)
        logging.debug(response)
        
    def get_tracks_from_album(self, album_id):
        response = self.request_from_spotify(
            'https://api.spotify.com/v1/albums/{}/tracks'.format(album_id), params=(('limit', '20'),))
        return json.loads(response.text)['items']

    def parse_message(self, update, context):
        url_match = self.find_all_urls_in_message(update.message.text)
        if url_match:
            self.url_found(update, context, url_match)
            for url in url_match:
                if "https://open.spotify.com" in url:
                    spot_id = url.split("/")[-1]
                    spot_id = spot_id.split("?")[0]
                    item_type = url.split("/")[3]
                    if item_type == "track":
                        self.add_to_playlist("spotify:track:{}".format(spot_id))
                        self.add_to_playlist("spotify:track:{}".format(
                            spot_id), playlist_id="2SLQtH9VdcXi2ToJC23FRq")  # just the singles
                    elif item_type == "album":
                        tracks = self.get_tracks_from_album(spot_id)
                        spotify_uris = "".join([j["uri"] + "," for j in tracks])
                        self.add_to_playlist(spotify_uris)

        number_finder = re.compile('[+-]\d*')
        number_match = number_finder.match(update.message.text)
        if number_match:
            try:
                number = int(number_match.group())
            except ValueError:
                pass
            else:
                self.count_plus1(update, context, number)

    def find_all_urls_in_message(self, text):
        url_match = re.findall(
            '(?:(?:https?|ftp):\/\/)?[\w/\-?=%.]+\.[\w/\-?=%.]+', text)
        return url_match

    def url_found(self, update, context, url_groups):
        for url in url_groups:
            context.chat_data.setdefault("all_urls_shared", [])
            context.chat_data["all_urls_shared"].append(url)

    def respond_to_message(self, context, update, text):
        if not self.silent:
            context.bot.send_message(
                chat_id=update.effective_chat.id, text=text)

    def count_plus1(self, update, context, number):
        given_by = update.effective_user.full_name
        given_to = update.message.reply_to_message.from_user.full_name
        if number > 0:
            context.chat_data.setdefault("most_upvoted_person", {})
            context.chat_data["most_upvoted_person"].setdefault(given_to, 0)
            context.chat_data["most_upvoted_person"][given_to] += 1
            context.chat_data.setdefault("most_upvotes_given", {})
            context.chat_data["most_upvotes_given"].setdefault(given_to, 0)
            context.chat_data["most_upvotes_given"][given_to] += 1
        elif number < 0:
            context.chat_data.setdefault("most_downvoted_person", {})
            context.chat_data["most_downvoted_person"].setdefault(given_to, 0)
            context.chat_data["most_downvoted_person"][given_to] += 1
            context.chat_data.setdefault("most_downvotes_given", {})
            context.chat_data["most_downvotes_given"].setdefault(given_to, 0)
            context.chat_data["most_downvotes_given"][given_to] += 1

        for url in self.find_all_urls_in_message(update.message.reply_to_message.text):
            if url.startswith("https://open.spotify.com"):
                song_name, artist = self.get_album_info_from_url(url)

            elif "https://youtu.be" in url:
                song_name = self.get_video_info(url)['title']
                artist = " youtube"

            try:
                text = "{0!s} has given {1:+d} to {2!s} from {3!s}".format(
                    update.effective_user.first_name, number, song_name, artist)
            except UnboundLocalError:
                pass
            else:
                song_id = "{}:{}".format(song_name, artist)
                self.update_vote_data(context.user_data, song_id, number)
                self.update_vote_data(context.chat_data, song_id, number)

                self.respond_to_message(context, update, text)

    def helpfunc(self, update, context):
        text = "You can call all of these functions \n Up/Down voting is done by replying to spotify/youtube links \n"
        for command in self.commands:
            text += "/{}: {}\n".format(command["command"],
                                       command["helpstring"])

        context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    def report_list(self, text, dict_data, asending=True, max_length=10):
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

    def upvotes(self, update, context):
        text = "Upvotes \n\n"
        try:
            text = self.report_list(
                text, context.chat_data["+1_given"], asending=True)
        except KeyError:
            text = "No upvotes found"
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    def my_upvotes(self, update, context):
        text = "Upvotes \n\n"
        try:
            text = self.report_list(
                text, context.user_data["+1_given"], asending=True)
        except KeyError:
            text = "No upvotes found"
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    def my_downvotes(self, update, context):
        text = "Downvotes \n\n"
        try:
            text = self.report_list(
                text, context.user_data["-1_given"], asending=False)
        except KeyError:
            text = "No downvotes found"
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    def downvotes(self, update, context):
        text = "Downvotes \n\n"
        try:
            text = self.report_list(
                text, context.chat_data["-1_given"], asending=False)
        except KeyError:
            text = "No downvotes found"
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    def my_stats(self, update, context):
        text = "My Stats \n"
        try:
            text += "Total Upvotes given is : {}\n".format(
                sum(context.user_data["+x_given"].values()))
            text += "\nMy top 5 most loved\n"
            text = self.report_list(
                text, context.user_data["+x_given"], max_length=5)
        except KeyError:
            pass

        try:
            text += "\nTotal Downvotes given is : {}\n".format(
                sum(context.user_data["-x_given"].values()))
            text += "\nMy top 5 most hated\n"
            text = self.report_list(
                text, context.user_data["-x_given"], max_length=5)
        except KeyError:
            pass

        context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    def refresh_token(self):
        logging.debug("Refreshing spotify token")
        auth_str = '{0}:{1}'.format(
            self.creds["client_id"], self.creds["client_secret"])
        b64_auth_str = base64.urlsafe_b64encode(auth_str.encode()).decode()

        headers = {'Authorization': 'Basic {0}'.format(b64_auth_str)}
        refresh_token = self.creds["spotify_refresh_token"]
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'redirect_uri': 'https://www.foo.com/auth'
        }
        response = requests.post(
            'https://accounts.spotify.com/api/token', headers=headers, data=data)
        self.spotify_token = json.loads(response.text)["access_token"]

    def request_from_spotify(self, request, params={}):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {}'.format(self.spotify_token),
        }

        response = requests.get(request,  headers=headers, params=params)
        spotify_data = json.loads(response.text)

        try:
            if spotify_data["error"]["message"] == "The access token expired":
                logging.warning("Token is bad")
                self.refresh_token()
                
        except KeyError:
            pass
        else:
            response = requests.get(request,  headers=headers, params=params)
            spotify_data = json.loads(response.text)

        return spotify_data

    def shutup(self, update, context):
        self.silent = True

    def shout(self, update, context):
        self.silent = False

    def run(self):
        self.updater.start_polling()
        self.updater.idle()

    def get_video_info(self, url):
        video_id = self.video_id_from_youtube_url(url)
        response = requests.get(
            "https://www.googleapis.com/youtube/v3/videos?id={}&key={}&fields=items(snippet(channelId,title,categoryId))&part=snippet".format(video_id, self.creds["google_api_key"]))
        return json.loads(response.text)['items'][0]['snippet']

    def video_id_from_youtube_url(self, url):

        m = re.match(
            "^.*(?:(?:youtu\.be\/|v\/|vi\/|u\/\w\/|embed\/)|(?:(?:watch)?\?v(?:i)?=|\&v(?:i)?=))([^#\&\?]*).*", url)
        if m:
            return m.groups()[0]
        else:
            return None


if __name__ == "__main__":
    tb = TelegramBot()
    tb.run()
