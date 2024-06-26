from dotenv import load_dotenv
import os

import pandas as pd
from google.oauth2.service_account import Credentials 
import gspread

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient
import json

from datetime import datetime
import pytz


#load my .env
load_dotenv()

#Spotify credentials
client_id_spotify = os.getenv("CLIENT_ID")  #get the value of an env variable
client_secret_spotify = os.getenv("CLIENT_SECRET")  
redirect_uri_spotify = 'http://localhost:8888/callback' #os.getenv("REDIRECT_URI")
auth_url_spotify = os.getenv("AUTH_URL")
token_url_spotify = os.getenv("TOKEN_URL")
api_base_url_spotify = os.getenv("BASE_URL")
scope_spotify = os.getenv("SCOPE_SPOTIFY")

#Google Chrome credentials
scope_google = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes = scope_google)
client = gspread.authorize(creds)
sheet_id = os.getenv("SHEET_ID")
workbook = client.open_by_key(sheet_id)
sheet_songs = workbook.worksheet("recently-played")

# Token file
TOKEN_FILE = 'spotify_token.json'

#timezone 
local_timezone = pytz.timezone('Europe/Paris')

#Create SpotifyOAuth object
sp_oauth= SpotifyOAuth(client_id=client_id_spotify, client_secret=client_secret_spotify, redirect_uri=redirect_uri_spotify, scope=scope_spotify)


def get_spotify_token():
    # Load token from file if it exists
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as token_file:
            token_info = json.load(token_file)
    else:
        token_info = None

    # Check if token is valid
    if token_info and not sp_oauth.is_token_expired(token_info):
        return token_info['access_token']
    else:
        # Refresh token if expired
        if token_info and 'refresh_token' in token_info:
            token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        else:
            # Perform initial authorization manually
            auth_url = sp_oauth.get_authorize_url()
            print(f'Please go to the following URL and authorize the application:\n{auth_url}')
            auth_code = input('Paste the authorization code here: ')
            token_info = sp_oauth.get_access_token(auth_code)
        
        # Save updated token to file
        with open(TOKEN_FILE, 'w') as token_file:
            json.dump(token_info, token_file)

        return token_info['access_token']
    

#store in gsheet
def store_in_google_sheets(data):
    #sheet_songs.clear() #we are not clearing it anymore because we want to keep track of all the songs 
    existing_rows = sheet_songs.get_all_values()
    start_index = len(existing_rows) + 1

    rows = []
    for track in data:
        rows.append([track['track_name'], track['artist_name'], track['album_name'], track['played_at'], track['duration_ms']])

    if rows:
        sheet_songs.batch_update([{
            'range': f'A{start_index}:E{start_index + len(rows) - 1}',
            'values': rows
        }])

#get last played song
def get_latest_played_at():
    played_at_values = sheet_songs.col_values(4)[1:]  # Skip the header
    if not played_at_values:
        return None

    played_at_values = [datetime.strptime(value, "%Y-%m-%d %H:%M:%S") for value in played_at_values]
    played_at_values_utc = [local_timezone.localize(value).astimezone(pytz.utc) for value in played_at_values]

    latest_played_at_utc = max(played_at_values_utc)
    latest_played_at_local = latest_played_at_utc.astimezone(local_timezone)

    latest_played_at_str = latest_played_at_local.strftime("%Y-%m-%d %H:%M:%S")
    
    #returns the latest timestamp as a string in the local time zone format
    return latest_played_at_str

#Fetch recently played tracks
def recently_played():
    token = get_spotify_token()
    sp = spotipy.Spotify(auth=token)
    recent_tracks = sp.current_user_recently_played(limit=50)

    tracks_info = []
    for item in recent_tracks['items']:
        track_name = item['track']['name']
        artist_name = item['track']['artists'][0]['name']
        album_name = item['track']['album']['name']
        played_at = item['played_at']
        duration_ms = item['track']['duration_ms']
        
        played_at_utc = datetime.fromisoformat(played_at.replace('Z', '+00:00'))
        local_datetime = played_at_utc.astimezone(local_timezone)
        local_datetime_str = local_datetime.strftime("%Y-%m-%d %H:%M:%S")

        tracks_info.append({
            'track_name': track_name,
            'artist_name': artist_name,
            'album_name': album_name,
            'played_at': local_datetime_str,
            'duration_ms': duration_ms 
        })
    
    sorted_tracks_info = sorted(tracks_info, key=lambda x: x['played_at'])

    #we get the lastest played song and by song i mean the date
    latest_played_at = get_latest_played_at()

    #if we do get a date, its filtering out the recently played tracks to only include those played after the latest track 
    if latest_played_at:
        #latest_played_at timestamp is converted into a datetime object using datetime.strptime()
        latest_played_at_dt = datetime.strptime(latest_played_at, "%Y-%m-%d %H:%M:%S")
        new_tracks_info = [track for track in sorted_tracks_info if datetime.strptime(track['played_at'], "%Y-%m-%d %H:%M:%S") > latest_played_at_dt]
    else:
        new_tracks_info = sorted_tracks_info

    store_in_google_sheets(new_tracks_info)

    return tracks_info


def main():
    results = recently_played()
    df = pd.DataFrame(results)
    print(df)

if __name__ == "__main__":
    main()

#print(recent_tracks, type(recent_tracks))
