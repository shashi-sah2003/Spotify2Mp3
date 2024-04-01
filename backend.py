from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pytube import YouTube
import csv
from googleapiclient.discovery import build
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from typing import List
import zipfile

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Load YouTube API key from file
with open("youtube_credentials.txt") as f:
    API_KEY = f.read().strip()

#extracting client id and client secret code in a secure way
with open("spotify_credentials.txt") as f:
    [SPOTIPY_CLIENT_ID, SPOTIFY_CLIENT_SECRET] = f.read().split("\n")
    f.close()

#Connecting with Spotify API
auth_manager = SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET)
sp = spotipy.Spotify(auth_manager=auth_manager)


def generate_playlist_csv(playlist_link, user_id):
    playlist_dict = sp.playlist(playlist_link)

    no_of_songs = playlist_dict["tracks"]["total"]

    album_list = []
    song_list = []
    release_date_list = []
    artists_list = []

    tracks = playlist_dict["tracks"]
    items = tracks["items"]
    offset = 0
    i = 0

    while i < no_of_songs:
        song = items[i-offset]["track"]["name"]
        album = items[i-offset]["track"]["album"]["name"]
        release_date = items[i-offset]["track"]["album"]["release_date"]
        artists = [k["name"] for k in items[i-offset]["track"]["artists"]]
        artists = ','.join(artists)
        album_list.append(album)
        song_list.append(song)
        release_date_list.append(release_date)
        artists_list.append(artists)

        if (i+1)%100 == 0:
            tracks = sp.next(tracks)
            items = tracks["items"]
            offset = i+1
        
        i+=1

    final_data = list(zip(song_list,artists_list,album_list,release_date_list))

    #Creating CSV File
    csv_file_name = f"{user_id}_final.csv"
    csv_file_path = os.path.join("csv_file", csv_file_name)


    with open(csv_file_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Artists", "Album", "Release Date"])
        writer.writerows(final_data)

    return csv_file_path



# Searching for a song on Youtube using YouTube Data API
def search_youtube(song_name, artist):
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    search_query = song_name + ' ' + artist + ' audio'
    request = youtube.search().list(
        q=search_query,
        part='id',
        type='video',
        maxResults=1
    )
    response = request.execute()
    if 'items' in response:
        if len(response['items']) > 0:
            video_id = response['items'][0]['id']['videoId']
            video_url = 'https://www.youtube.com/watch?v=' + video_id
            return video_url
    print(f"No search results found for '{song_name}' by {artist}.")
    return None

# Download MP3 from YouTube using pytube
def download_mp3(youtube_url, user_folder):
    try:
        yt = YouTube(youtube_url)
        stream = yt.streams.filter(only_audio=True).first()
        if stream:
            print("Downloading MP3...")

            os.makedirs(user_folder, exist_ok=True)
            file_name = f"{yt.title}.mp4"
            # song_path = os.path.join(user_folder, f"{yt.title}.mp4")
            stream.download(output_path=user_folder)
            print("Download complete.\n")
            return file_name
        else:
            print("No audio stream available for this video.")
    except Exception as e:
        print(f"Error downloading MP3: {e}")
        

#Loading song details from CSV
def load_song_details(csv_file):
    song_details = []
    with open(csv_file, 'r', newline='') as f:
        reader = csv.reader(f)
        next(reader) #skipping header
        for row in reader:
            song_details.append(row[:2])
    
    return song_details


@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    # Render the HTML template
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/download_songs", response_class=HTMLResponse)
async def download_songs(request: Request, playlist_link: str = Form(...), userid: str = Form(...)):

    print(userid)
    print(playlist_link)
    #Generating CSV file for the playlist
    csv_file_path = generate_playlist_csv(playlist_link, userid)
    print("CSV file is created")

    user_folder = os.path.join("downloaded_songs", userid)
    os.makedirs(user_folder, exist_ok=True)

    song_details = load_song_details(csv_file_path)
    downloaded_songs = []
    

    for song_name, artist in song_details:
        youtube_url = search_youtube(song_name, artist)
        if youtube_url:
            song_file = download_mp3(youtube_url, user_folder)
            if song_file:
                #encoded_file_name = urllib.parse.quote(song_file, safe="")
                downloaded_songs.append(song_file)
    
    response_data = {
        "message": "Songs downloaded successfully!",
        "user_folder": user_folder,
        "songs": downloaded_songs
    }

    return JSONResponse(content=response_data)

@app.get("/download/{user_id}/{file_name}")
async def download_song(user_id: str, file_name: str):
    user_folder = os.path.join("downloaded_songs", user_id)
    file_path = os.path.join(user_folder, file_name)
    return FileResponse(file_path, media_type='audio/mp3', filename=file_name)
