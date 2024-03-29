
from distutils.command.config import config
import re
import os
import datetime

import argparse
from DBModule import getDBConnection
import TranslatorApp.Configuration as Configuration


from AIDubbing.AzureSynthesizer import AzureSynthesizer
from AIDubbing.ElevenLabSynthesizer import ElevenLabSynthesizer

def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTIONS] [YT-VIDEO]...",
        description="Generate an AI-Dubbed Version based on German Subtitles"
    )
    parser.add_argument(
        "--version", action="version",
        version = f"{parser.prog} version 1.0.0"
    )

    parser.add_argument('--voice', help="Choose one of the configured voices",
                        action='store')

    parser.add_argument('-d', '--download',
                    action='store_true', help='Only Download the Video and Subtitle')

    parser.add_argument('-b', '--backgroundMusic',
                    action='store_true', help='Mix the Background Music with synthesized voice')

    parser.add_argument('--audioOnly',
                    action='store_true', help='Synthesize Audio Only, no video merging (e.g. for Talk-Troughs)')

    parser.add_argument('--skipSynth',
                    action='store_true', help='Skip synthesizing with AI Voices')


    parser.add_argument('videos', nargs='*', help="list of YT-Video-IDs or KA Lesson")

    return parser


#TODO: change to load lesson from DataBase
def isYT(video_id):
    # Regular expression pattern for a valid YouTube video ID
    pattern = r'^[a-zA-Z0-9_-]{11}$'
    match = re.match(pattern, video_id)
    
    return match is not None

# Main Fucntion to generate AI-Dubbing for a YT-Video
def processVideo(YTid):
    print("Processing YT Video " + YTid)

    if (args.audioOnly):
        kind="Talktrough"
    else:
        kind="Video"

    try:

        if ( Configuration.tts == "elevenlabs"):
            synth = ElevenLabSynthesizer(YTid, kind, args)
        else:
            synth = AzureSynthesizer(YTid, kind, args)

        #load Subtitles and generate SSML
        synth.readSubtitles()


        #if not DownloadOnly
        if (not args.download):
            #Synthesize Audio and Merge to one MP3
            synth.synthesizeAudio()

            if (not args.audioOnly):
                synth.splitVideo()

        #Generate Youtube Title & Description for Copy Pasting
        synth.generateYoutubeData()

    except ValueError as e:
        print(repr(e))
        exit()

if __name__ == '__main__':
    print("KA-Deutsch AI-Dubbing")

    parser = init_argparse()
    args = parser.parse_args()
    dbConnection = getDBConnection()


    if len(args.videos) == 0:

        #print("No Videos specified, generating last 3 translated videos"), removed or kind='Talktrough' from SQL temporary until speed for Talktroughs is fixed #3
        sql = "SELECT * FROM %s.`ka-content`" % Configuration.dbDatabase + " WHERE (kind='Video') AND translation_status = 'Translated' AND (local_video IS NULL OR local_video = '') GROUP BY id ORDER BY translation_date DESC LIMIT 3"

        print("No Videos specified, generating last 3 translated videos")
        with dbConnection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()
            for row in result:
                print( "%s: %s with ytID %s" % (row['kind'], row['original_title'], row['youtube_id']))
                processVideo( row['youtube_id'] )

        sql = "SELECT * FROM %s.`ka-content`" % Configuration.dbDatabase + " WHERE (kind='Video' or kind='Talktrough') AND translation_status = 'Approved' GROUP BY id ORDER BY review_date DESC LIMIT 30"
        with dbConnection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()
            i=0;
            for row in result:
                #Check if approval date is newer than timestamp of local_video
                print( "%s: %s : %s" % (row['original_title'], row['review_date'], row['local_video']))
                lVideo = row['local_video']
                if ( lVideo is not None):
                    fileTimestamp = os.path.getmtime('.' + os.sep + 'TranslatorApp' + os.sep + row['local_video']);
                    if (fileTimestamp < datetime.datetime.fromisoformat(str(row['review_date'])).timestamp()):
                        print("Approval newer than existing Video, processing")
                        processVideo( row['youtube_id'] )
                else:
                    print("Processing.....")
                    processVideo( row['youtube_id'] )

                # Stop processing after 3 videos
                i=i+1
                if (i>3):
                    print("Terminating after 3 videos")
                    exit()

        exit()

    else:
        for YTid in args.videos:

            #Check if this is lesson or a YTID
            if (not isYT(YTid)):    
                print("This is a Khan Academy Lesson, loading all videos/talktroughs")
                with dbConnection.cursor() as cursor:
                    sql = "SELECT * FROM %s.`ka-content`" % Configuration.dbDatabase + " where (kind='Video' or kind='Talkthrough') and lesson='%s'" % YTid
                    cursor.execute(sql)
                    #result = cursor.fetchall()
                
                    for row in cursor.fetchall():
                        print( "%s: %s: YT %s" % (row['kind'], row['original_title'], row['youtube_id']))
                        processVideo( row['youtube_id'] )

                    print("Now we should process them download/syntesize/mergeVideo")
            else:
                processVideo(YTid)

        exit()

