import json
from googleapiclient.discovery import build
from googleapiclient.errors import Error
from youtube_dl import YoutubeDL

#read keys.json to get api keys
keys_json = open("keys.json", "r")
keys = json.load(keys_json)



#returns a list of dicts of video titles and video ids given a youtube playlist id
def get_playlist_details(playlist_id):

    #GET request to youtube API to obtain titles and ids of youtube playlist items
    with build('youtube', 'v3', developerKey=keys["API"]["youtube"]) as service:
        song_responses = [] #stores responses
        song_details = [] #list of dictionaries with all video's title and id 
        request = service.playlistItems().list(
            part = "snippet",
            playlistId = playlist_id,
            maxResults = 50
            )
        response = request.execute()
        song_responses.append(response)
        
        #gets all the videos in playlist if playlist has more than 50 items
        #this is because youtube api has maximum of 50 items per request
        while "nextPageToken" in response:
            nextPageToken = response["nextPageToken"]
            request = service.playlistItems().list(
            part = "snippet",
            playlistId = playlist_id,
            maxResults = 50,
            pageToken = nextPageToken
            )
            response = request.execute()
            song_responses.append(response)

        #get the title and id of all videos in the playlist and append to list "song_details"
        for response in song_responses:
            for song in response["items"]:
                title = song["snippet"]["title"]
                vid_id = song["snippet"]["resourceId"]["videoId"]
                if title != "Deleted video" and title != "Private video":
                    song_details.append({
                        "title" : title,
                        "id" : vid_id
                    })

        return song_details


#returns a dict of video title and video id given a youtube query (works with individual youtube links and video ids)
def get_video_details(query):

    #GET request to get individual video details
    with build('youtube', 'v3', developerKey=keys["API"]["youtube"]) as service:
        request = service.search().list(
            part = "snippet",
            maxResults = 1,
            type = "video",
            q = query,
            order = "relevance"
            )
        response = request.execute()
        #package title and video id in a dictionary
        title = response["items"][0]["snippet"]["title"]
        vid_id = response["items"][0]["id"]["videoId"]
        song_details = {
            "title" : title,
            "id" : vid_id
        }

        return song_details

def get_video_details_id(id):
    with build('youtube', 'v3', developerKey=keys["API"]["youtube"]) as service:
        request = service.videos().list(
            part = "snippet",
            maxResults = 1,
            id = id
            )
        response = request.execute()
        #package title and video id in a dictionary
        title = response["items"][0]["snippet"]["title"]
        vid_id = id
        song_details = {
            "title" : title,
            "id" : vid_id
        }

        return song_details



#returns youtube video audio source url given a query(str)
def get_audio_url(url):
    ydl_options = {'format': 'bestaudio', 'noplaylist':'False', "cookiefile": "cookies.txt"}
    with YoutubeDL(ydl_options) as ydl:
        try: 
            info = ydl.extract_info(url = url, download=False)
            audio_url = info['formats'][0]['url']
            details = {
                "success" : True,
                "source" : audio_url,
            }
        except: 
            print("failed to download")
            details = {
                "success" : False
            }
        return details



#return playlist or video id given a playlist url
def get_id(url):
    url = url.split("=")
    id = url[-1]
    return id