import pymysql
import google.auth.transport.requests
import requests
from datetime import datetime, date
import TranslatorApp.Configuration as Configuration
from DBModule import getDBConnection


from pytube import YouTube
from googleapiclient.discovery import build

def getVideoData(ytID, dbConnection):

    # Get the number of views using the YouTube Data API

    youtube = build('youtube', 'v3', developerKey=Configuration.googleAPI)
    video_stats = youtube.videos().list(part='statistics', id=ytID).execute()

    if ( len(video_stats['items']) > 0 and 'statistics' in video_stats['items'][0]):
        if 'viewCount' in video_stats['items'][0]['statistics']:
            views = video_stats['items'][0]['statistics']['viewCount']
        else:
            views = 0

        if 'dislikeCount' in video_stats['items'][0]['statistics']:
            dislikes = video_stats['items'][0]['statistics']['dislikeCount']
        else:
            dislikes = 0

        if 'likeCount' in video_stats['items'][0]['statistics']:
            likes = video_stats['items'][0]['statistics']['likeCount']
        else:
            likes = 0

        if 'commentCount' in video_stats['items'][0]['statistics']:
            comments = video_stats['items'][0]['statistics']['commentCount']
        else:
            comments = 0

    
        with dbConnection.cursor() as cursor:
            sql = "UPDATE `ka-content` SET `yt_views` = '%s', `yt_comments` = '%s', `yt_likes` = '%s', `yt_dislikes` = '%s' WHERE `translated_youtube_id` = '%s'" % (views, comments, likes, dislikes, ytID)
            cursor.execute(sql)
            dbConnection.commit()

        return 1

    else:
        print("Video Stats not found for %s" % ytID)
        return 0


def getGermanVideos():
    # Get the German videos from the database

    dbConnection = getDBConnection()

    updateCount = 0

    with dbConnection.cursor() as cursor:

        sql = "SELECT original_title, youtube_id, translated_youtube_id, creation_date FROM `ka-content` WHERE youtube_id <> translated_youtube_id AND translated_youtube_id <> '' GROUP BY translated_youtube_id"
        cursor.execute(sql)
        result = cursor.fetchall()
        all = False

        for row in result:
            
            date_obj = datetime.strptime(row['creation_date'], '%Y-%m-%dT%H:%M:%SZ')
            weekday = date_obj.weekday()
            today = date.today()

            if weekday == today.weekday() or all==True:
                updateCount += getVideoData(row['translated_youtube_id'], dbConnection)

    print("Updated Stats for %s videos" % updateCount)

if __name__ == '__main__':
    getGermanVideos()