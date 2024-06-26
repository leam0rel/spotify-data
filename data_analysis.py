import pandas as pd
import re
from datetime import datetime, timedelta

from dotenv import load_dotenv
import os

import pandas as pd
from google.oauth2.service_account import Credentials 
import gspread


import ssl 
import smtplib
from email.message import EmailMessage


#load my .env
load_dotenv()

#Google Chrome credentials
scope_google = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes = scope_google)
client = gspread.authorize(creds)
sheet_id = os.getenv("SHEET_ID")
workbook = client.open_by_key(sheet_id)
sheet_data = workbook.worksheet("analysis")
sheet_songs = workbook.worksheet("recently-played")

#email
email_sender = os.getenv("EMAIL_SENDER")
email_recipient = os.getenv("EMAIL_RECIPIENT")
email_password = os.getenv("EMAIL_PASSWORD")



#filter the data to get the week before til now
def filter_weekly_data(df):
    today = datetime.now()
    start_of_current_week = today 
    start_of_previous_week = start_of_current_week - timedelta(weeks=1)

    start_time = start_of_previous_week.replace(hour=today.hour, minute=today.minute, second=today.second)
    end_time = start_of_current_week.replace(hour=today.hour, minute=today.minute, second=today.second)
    
    df['Played at'] = pd.to_datetime(df['Played at'])
    
    # Filter data within the specified time range
    
    filtered_df = df[(df['Played at'] >= start_time) & (df['Played at'] < end_time)]

    return start_time,end_time,filtered_df

#store in gsheet
def store_analysis_data(start_of_week, end_of_week, album_week, total_minutes, total_hours, top_artists, top_tracks):
    existing_rows = sheet_data.get_all_values()
    start_index = len(existing_rows) + 1
    
    row = [
        start_of_week.strftime("%Y-%m-%d %H:%M:%S"),
        end_of_week.strftime("%Y-%m-%d %H:%M:%S"),
        total_minutes,
        total_hours
    ]

    for _, row_data in album_week.iterrows():
        row.append(row_data['Album Name'])
        

    for _, row_data in top_artists.iterrows():
        row.append(row_data['Artist Name'])
        row.append(row_data['Play Count'])
    
    for _, row_data in top_tracks.iterrows():
        row.append(row_data['Track Name'])
        row.append(row_data['Play Count'])
    
    sheet_data.insert_row(row, start_index)

#get all the artists i have listened to this week
def get_unique_artists(filtered_df):
    
    artist_counts = filtered_df.groupby('Artist Name').size().reset_index(name='Song Count')
    unique_artists = filtered_df['Artist Name'].unique()
    
    return artist_counts

#get my top 5 artists    
def get_top_artist(filtered_df, n=5):   
   
    top_artist = filtered_df.groupby('Artist Name').size().reset_index(name='Play Count')
    top_artist = top_artist.sort_values(by='Play Count', ascending=False).head(n)
    
    return top_artist    

#get my top 5 songs
def get_top_songs(filtered_df, n=5):   
    
    top_songs = filtered_df.groupby('Track Name').size().reset_index(name='Play Count')
    top_songs = top_songs.sort_values(by='Play Count', ascending=False).head(n)
    
    return top_songs

#get the album of the week
def get_album_of_the_week(filtered_df, n=1):   
    
    album_week = filtered_df.groupby('Album Name').size().reset_index(name='Play Count')
    album_week = album_week.sort_values(by='Play Count', ascending=False).head(n)
    
    return album_week

#get the minutes ive sent on spotify
def get_amount_of_time(filtered_df):   
    
    total_duration_ms = filtered_df['Track Duration'].sum()
    total_duration_minutes = total_duration_ms / 60000  
    total_duration_hours = total_duration_minutes / 60  
    return total_duration_minutes, total_duration_hours

#body of the email 
def generate_email_body(start_week, end_week, album_of_the_week, top_artists, top_tracks, total_minutes, total_hours):
    body = f"Analysis from {start_week} to {end_week}\n\n"
    body += "Album of the Week:\n"
    for _, row in album_of_the_week.iterrows():
        body += f"{row['Album Name']}: {row['Play Count']} plays\n\n"
    body += "Top 5 Artists:\n"
    for _, row in top_artists.iterrows():
        body += f"{row['Artist Name']}: {row['Play Count']} plays\n"
    body += "\nTop 5 Songs:\n"
    for _, row in top_tracks.iterrows():
        body += f"{row['Track Name']}: {row['Play Count']} plays\n"
    body += f"\nTotal Listening Time: {total_minutes:.2f} minutes ({total_hours:.2f} hours)\n"
    return body
  
#email sender    
def send_email(subject, body, email_sender, email_recipient, email_password):
    em = EmailMessage()
    em['From'] = email_sender
    em['To'] = email_recipient
    em['Subject'] = subject
    em.set_content(body)

    context = ssl.create_default_context()

    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
        smtp.login(email_sender,email_password)
        smtp.sendmail(email_sender,email_recipient, em.as_string())

    
    print("Email sent successfully.")


def main():
    df = pd.DataFrame(sheet_songs.get_all_records())
    #print(df.head())
    start_time,end_time,filtered_df = filter_weekly_data(df)

    start_week = start_time.strftime("%Y-%m-%d %H:%M:%S")
    end_week = end_time.strftime("%Y-%m-%d %H:%M:%S")
    album_of_the_week = get_album_of_the_week(filtered_df, n=1)
    artists = get_unique_artists(filtered_df)
    top_artists = get_top_artist(filtered_df, n=5)
    top_tracks = get_top_songs(filtered_df, n=5)
    total_minutes, total_hours = get_amount_of_time(filtered_df)

    print(start_week,end_week)
    print("Album of the week:\n", album_of_the_week)
    print("Unique Artists and Song Counts:\n", artists)
    print("\nTop 5 Artists:\n", top_artists)
    print("\nTop 5 Songs:\n", top_tracks)
    print(f"\nTotal Listening Time: {total_minutes:.2f} minutes ({total_hours:.2f} hours)")

    store_analysis_data(start_time, end_time, album_of_the_week, total_minutes, total_hours, top_artists, top_tracks)
    email_body = generate_email_body(start_week, end_week, album_of_the_week, top_artists, top_tracks, total_minutes, total_hours)
    send_email("Weekly Music Analysis", email_body, email_sender, email_recipient, email_password)



if __name__ == "__main__":
    main()

    
#problem i have noticed : it all work, but when i send a mail at 11:08 am, the email has the date at 9am (utc format problem) ?
# TOFIX








