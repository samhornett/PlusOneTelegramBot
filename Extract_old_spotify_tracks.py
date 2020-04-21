import json
import base64
import requests
import webbrowser

from telegram.ext import PicklePersistence

with open("secrets.json", 'r') as f:
            creds = json.load(f)

auth_str = '{0}:{1}'.format(
    creds["client_id"], creds["client_secret"])
b64_auth_str = base64.urlsafe_b64encode(auth_str.encode()).decode()

def add_to_playlist(token, track_id , playlist_id = "4TgBbmOB7T1c5Dso2dpgny"):
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer {}'.format(token),
    }

    params = (
    ('position', '0'),
    ('uris', track_id),
    )

    response = requests.post('https://api.spotify.com/v1/playlists/{}/tracks'.format(playlist_id), headers=headers, params=params)
    print(response.content)

# https://accounts.spotify.com/authorize?client_id=650f00768efc4e8e963a961b8d986a06&response_type=code&redirect_uri=https://www.foo.com/auth&state=bob&scope=playlist-modify-public playlist-modify-private

def refresh_token():

    headers = {'Authorization': 'Basic {0}'.format(b64_auth_str)}
    refresh_token = creds["spotify_refresh_token"]
    data = {
    'grant_type': 'refresh_token',
    'refresh_token': refresh_token,
    'redirect_uri': 'https://www.foo.com/auth'
    
    }

    response = requests.post('https://accounts.spotify.com/api/token', headers=headers, data=data)
    return json.loads(response.text)["access_token"]




if __name__ == "__main__":
    botdata = PicklePersistence(filename="botdata")

    chat_data = botdata.get_chat_data()

    print(chat_data["all_urls_shared"])

    with open("spotify_tracks.json", 'w') as f:
        json.dump(chat_data["all_urls_shared"], f)
    #token = refresh_token()
    #add_to_playlist(token, "spotify:track:5gW5dSy3vXJxgzma4rQuzH")



