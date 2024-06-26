# spotify-data
Spotify "application" that pulls my personal data and store it in a Google spreadsheet.

This is the public version : the workflows are not available in this repository :)

The goal is to use the Spotify API and the Google spreadsheet API. I want to store my personal data in this spreadsheet. Every 3 hours, my listening data will be stored in a google sheet tab, as the script will be automated with github workflows. Then this data will be sorted in different categories : amount of minutes listened to spotify this week, top 5 artists of the week (and number of songs for each artist), top 5 songs of the week (and amount of time I have listened to the song for each song), then finally album of the week.

And finally, this summary will be sent on my email address every monday morning between 9am and 10am so I can have my "spotify wrapped" at the beginning of each week.
