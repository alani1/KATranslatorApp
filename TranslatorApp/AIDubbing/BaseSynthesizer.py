
from distutils.command.config import config
import os
import sys
import re
import csv
from webbrowser import get
import pytube
import requests


from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.compositing.concatenate import concatenate_videoclips
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.editor import vfx, concatenate_audioclips

from jinja2 import Environment, FileSystemLoader

import TranslatorApp.Configuration as Configuration
import AIDubbing.Configuration as AIConfiguration
from DBModule import getDBConnection



class BaseSynthesizer:
    """Base Syntehsizer Class to Merge Subtitles and generate Audio"""

    def __init__(self, YTid, kind="Video", voice=""):
        """Constructor"""

        self.speedFactor = 1.0
        
        self.azureSentencePause = 'default'
        self.languageCode = "de-DE"
        self.voices = AIConfiguration.voices

        self.YTid = YTid
        self.kind = kind
        # If voice exists load the Voice from Configuration File
        if (voice in AIConfiguration.voices):
            self.voice = AIConfiguration.voices[voice]
        else:
            self.voice = AIConfiguration.voices[AIConfiguration.defaultVoice]

        self.voiceName = self.voice['voiceName']
        self.synth_voice_gender = self.voice['voiceGender']
        self.speedFactor = self.voice['speedFactor']

        self.amaraAPI = Configuration.amaraAPI

        self.merged_subtitles = []
        

        self.dbConnection = getDBConnection()
        with self.dbConnection.cursor() as cursor:
            sql = "SELECT * FROM %s.`ka-content`" % Configuration.dbDatabase + " where youtube_id='%s'" % self.YTid
            cursor.execute(sql)
            self.dbData = cursor.fetchone()

        self.workingDirectory = '.' + os.sep + 'workingFolder'
        self.dataDirectory = '.' + os.sep + 'TranslatorApp' + os.sep + 'static' + os.sep + 'data' + os.sep + self.dbData['course'] + os.sep + self.dbData['unit'] + os.sep + self.dbData['lesson']
        #create directory if it does not exist
        if not os.path.exists(self.dataDirectory):
            os.makedirs(self.dataDirectory)

        # extract the last directory from the slug
        self.name = self.dbData['slug'].split('/')[-1]
        print("Name:" + self.name)


        self.videoURL = "https://www.youtube.com/watch?v=" + self.YTid
        self.videoFile = os.path.join(self.dataDirectory, f"{self.name}.mp4")
        self.subtitleFile = os.path.join(self.dataDirectory, f"{self.name}-de.srt")

        #Download Video from Youtube if it does not yet exist
        if not os.path.isfile(self.videoFile):
            print("Downloading Video from " + self.videoURL)
            #Use OAuth to avoid Error with age restricted videos
            youtube = pytube.YouTube(self.videoURL, use_oauth=True, allow_oauth_cache=True)
            video = youtube.streams.filter(progressive=True).order_by('resolution').desc().first()
            video.download(self.dataDirectory, f"{self.name}.mp4")

        #Download German Subtitle from Amara.org if it does not yet exist
        #TODO
        if not os.path.isfile(self.subtitleFile):
            amaraURL = self.getAmaraSubtitleURL()
            if (len(amaraURL) > 0):
                print("Downloading German Subtitle from %s" % amaraURL)
                self.deSubtitle = requests.get(amaraURL)
                ## Write to File
                if(len(self.deSubtitle.text) > 0 ):
                    with open(self.subtitleFile, 'w', newline='\n') as file:
                        file.write(self.deSubtitle.text)
                        file.close()

    # Identify the correct URL for Downloading the German Subtitle from Amara.org
    def getAmaraSubtitleURL(self):
       # Load the Amara ID
        url = "https://amara.org/api/videos/?video_url=https://www.youtube.com/watch?v=" + self.YTid
        headers = {'X-api-key': self.amaraAPI} 
        response = requests.get(url,headers).json()
        #return jprint(response)
        #make this more robust to handle when no result is found
        if ( response["meta"]["total_count"] > 0 and response.get('objects') != None and len(response['objects']) > 0):
            #iterate as there may be multiple IDs and find the khan-academy team
            
            for vid in response['objects']:
                
                amaraID = vid['id']
                #Select only Videos from Team Khan-Academy 
                if (vid['team'] == "khan-academy"):
                    
                    for lang in vid['languages']:
                        if lang['name'] == "German":
                            return "https://amara.org/api/videos/%s/languages/de/subtitles/?format=srt" % amaraID

        print("ERROR: German Subtitle could not be found!")
        return ""


# =============================================================================================================================

# ======================================== SRT Subtitle Processing and SSML Generation=========================================


    def readSubtitles(self):
        """Read Subtitle File"""
        #Open file and read srt-format subtitles into array

        #self.subtitleFile = filename

        # Open the .srt file
        with open(self.subtitleFile, 'r') as f:
            srt_data = f.read()

        # Split the .srt data into subtitle blocks
        subtitle_blocks = srt_data.split('\n\n')
        #print(subtitle_blocks)
    
        # Merge the subtitles
        self.merge_subtitles(subtitle_blocks)

    # Define a function to convert a time string to seconds
    def time_to_seconds(self, time_str):
        hours, minutes, seconds = map(float, time_str.replace(',', '.').split(':'))
        return hours * 3600 + minutes * 60 + seconds                

    #Merge subtitles based on length of pauses
    #this splits the subtitles and later the video into smaller chunks which reduced the time drift as german is spoken slower than english
    def merge_subtitles(self, subtitle_blocks, pause_time=0.5):
        
        current_subtitle = dict(content='', ssml='', start=0, end=0, char_rate=0)
        current_end_time = 0

        #print("Subtties debugging")
        for subtitle in subtitle_blocks:
            # Split the subtitle into lines and extract the start and end times
            lines = subtitle.split('\n')
            #print(lines)
            start_time, end_time = lines[1].split(' --> ')
            start_time = self.time_to_seconds(start_time)
            end_time = self.time_to_seconds(end_time)
            duration = end_time - start_time

            content = ''
            #join subtitles with multiple lines
            for i in range(2,len(lines)):
                content += lines[i] + ' '

            #print(content)
            #print("duration: " + str(duration))
            #print("pause: " + str(start_time - current_end_time))
            #print("\n")

            # Check if there is a pause between this subtitle and the current one
            # Create new Chunk if length of pause above threshold or ( maximum lenght of subtitle is too long)
            # Handle special case when there is a pause at the begging of video (curren_end_time = 0)
            if current_end_time > 0 and start_time - current_end_time > pause_time:

                #here we calculate the char_rate of the subtitle just bfore storing it
                current_subtitle['char_rate'] = len(current_subtitle['content']) / ( current_subtitle['end'] - current_subtitle['start'])                
                self.merged_subtitles.append(current_subtitle)
                current_subtitle = dict(content='', ssml='', start=0, end=0, char_rate=0)
                current_subtitle['content'] = content.strip() + " "
                current_subtitle['start'] = start_time
                current_subtitle['end'] = end_time
            else:
                current_subtitle['content'] += content.strip()  + " "
                current_subtitle['end'] = end_time

            current_end_time = end_time
        # Add the last subtitle to the merged subtitles
        current_subtitle['char_rate'] = len(current_subtitle['content']) / ( current_subtitle['end'] - current_subtitle['start'])                
        self.merged_subtitles.append(current_subtitle)
        return self.merged_subtitles                


# =============================================================================================================================

# ======================================== Audio Synthesizing and processing ==================================================

    def synthesizeAudio(self):

        i = 1
        audio_segments = []
        for subtitle in self.merged_subtitles:

            filePath = os.path.join(self.workingDirectory, f'{self.name}-{str(i)}.wav')

            # check if filePath exists and is newer than self.subtitleFile
            # if yes, then the audio file is already synthesized
            # if no, then the audio file needs to be synthesized

            # Only synthesize if the audio file doesn't exist, avoid unnecessary calls to Speech Services
            if not os.path.exists(filePath) or os.path.getmtime(self.subtitleFile) > os.path.getmtime(filePath):

                # Prepare output location. If folder doesn't exist, create it
                if not os.path.exists(os.path.dirname(filePath)):
                    try:
                        os.makedirs(os.path.dirname(filePath))
                    except OSError:
                        print("Error creating working folder")
            
                # Produce synthesized audio as WAV for the subtitle under filePath
                self.synthesizeSingleSubtitle(subtitle, filePath)

            audio_segments.append(AudioFileClip(filePath))
            subtitle["audioFile"] = filePath
            #print("Saving Audio: " + audio.properties)
                            
            i += 1

        output_clip = concatenate_audioclips(audio_segments)

        outputFile = os.path.join(self.workingDirectory, f'{self.name}.mp3')
        output_clip.write_audiofile(outputFile)

        # For Talktroughs write the outputfile also to the data directory
        if self.dbData['kind'] == 'Talkthrough':
            outputFileData = os.path.join(self.dataDirectory, f'{self.name}-DE.mp3')
            output_clip.write_audiofile(outputFileData)


    # Split and Assemble the Video with synthesized Audio
    def splitVideo(self):

        print("Splitting Video")
        
        video_clip = VideoFileClip(self.videoFile)
        print("FPS %s" % video_clip.fps)
        finalVideoFileName = os.path.join(self.dataDirectory, f'{self.name}-DE.mp4')
        clips = []

        i = 1
        for s in self.merged_subtitles:
            start = s["start"]
            end = s["end"]

            audioFileName = os.path.join(self.workingDirectory, f'{self.name}-{str(i)}.wav')
            videoFileName = os.path.join(self.workingDirectory, f'{self.name}-{str(i)}.mp4')

            audio_clip = AudioFileClip(audioFileName)
            audioDuration = audio_clip.duration

            print("\nChunk %s: %s, %s" % (i, start, end))
            print("Videoduration: %f" % float(end - start))
            print("Audioduration: %f" % audioDuration)

            clip = video_clip.subclip(start, end)
            # new clip with new duration, slowdown the video by Ratio
            ratio = float(end-start) / audioDuration
            new_clip = clip.fx( vfx.speedx,ratio)
            myClip = new_clip.set_audio(audio_clip)
            myClip.write_videofile(videoFileName)
            clips.append(videoFileName)

            audio_clip.close()
            clip.close()
            myClip.close()
            new_clip.close()

            i += 1

        # concatenating all the clips
        print("\nMerging %s Clips" % len(clips))
        clipArray = []
        for i in clips:
            # TODO: Fix Audio Glitches
            # Audio glitches are happening when concatenativng the Video Clips
            # This is not happening in the merge MP3 File in synthsize Audio
            # Maybe fadein and fadeout can help
            #clipArray.append(VideoFileClip(i).audio_fadein(0.01).audio_fadeout(0.01))
            clipArray.append(VideoFileClip(i))

        final = concatenate_videoclips(clipArray)
        #writing the video into a file / saving the combined video
        final.write_videofile(finalVideoFileName)

        # If status is "Translated" store the final Video File in the DB
        dbConnection = getDBConnection()
        if (self.dbData['local_video'] == None or len(self.dbData['local_video']) == 0):
            # Escape finalVideoFileName for SQL
            webVideoName = finalVideoFileName.replace("\\", "/")
            # remove prefix "./TranslatorApp" from webVideoName
            webVideoName = webVideoName.replace("./TranslatorApp", "")
            sql = "UPDATE %s.`ka-content`" % Configuration.dbDatabase + " SET local_video = '%s' where youtube_id = '%s'" % (webVideoName, self.YTid)
            print(sql)
            with dbConnection.cursor() as cursor:
                cursor.execute(sql)
            
            dbConnection.commit()

        

# =============================================================================================================================

# ======================================== Youtube Functions =============== ==================================================

    def getKAData(self, type, name):

        #Load Data from lesson record, check the Caps for type in Kind it needs to start with capital letter
        sql = "SELECT * FROM %s.`ka-content`" % Configuration.dbDatabase + " where kind = '%s' and %s = '%s'" % (type.capitalize(), type, name)
        dbConnection = getDBConnection()
        with dbConnection.cursor() as cursor:
            cursor.execute(sql)
            for row in cursor.fetchall():
                return row

    # Generates the Youtube Description for the Video and save it to the DataBase
    def generateYoutubeData(self):

        environment = Environment(loader=FileSystemLoader("TranslatorApp/templates"))
        template = environment.get_template("YTDescription.txt")


        dbConnection = getDBConnection()
        with dbConnection.cursor() as cursor:
            sql = "SELECT * FROM %s.`ka-content`" % Configuration.dbDatabase + " where youtube_id = '%s'" % self.YTid
            cursor.execute(sql)
            #print(sql)
            for row in cursor.fetchall():            
                values = {}

                values['title'] = row['translated_title']
                values['kaLink'] = row['canonical_url']

                domain = self.getKAData("domain", row['domain'])
                values['domain'] = domain['translated_title']

                course = self.getKAData("course", row['course'])
                values['course'] = course['translated_title']

                unit = self.getKAData("unit", row['unit'])
                values['unit'] = unit['translated_title']

                lesson = self.getKAData("lesson", row['lesson'])
                values['lesson'] = lesson['translated_title']
                values['description'] = lesson['translated_description_html']
                
                #nextLesson
                #previousLesson
                #select all rows with same lesson
                sql = "SELECT * FROM %s.`ka-content`" % Configuration.dbDatabase + " where lesson = '%s'" % row['lesson']
                with dbConnection.cursor() as cursor2:
                    cursor2.execute(sql)
                    contents = cursor2.fetchall()
                    i = 0
                    for content in contents:
                        if(content['id'] == row['id']):
                            #print("found the same id and it is row %s" % i)
                            values['previousLesson'] = contents[i-1]['canonical_url']
                            values['nextLesson'] = contents[i+1]['canonical_url']
                        i+=1
                
                #translator
                if (row['translator'] != None and len(row['translator']) > 0):
                    values['translator'] = row['translator'].capitalize() + " von "

                # generate lessonDescription, takes the course description and adds the unit description
                c = AIConfiguration.courseDescriptions[row['course']]
                values['lessonDescription'] = c['description'] + c[row['unit']]

                #channelLink
                values['channelLink'] =AIConfiguration.courseDescriptions[row['course']]['channelLink']

                content = template.render(values)
                #print(values)

                # Save the generated Description to the DB

                sql = "UPDATE %s.`ka-content`" % Configuration.dbDatabase + " SET yt_description = '%s' where youtube_id = '%s'" % (content, self.YTid)
                with dbConnection.cursor() as cursor:
                    cursor.execute(sql)
                dbConnection.commit()


                #print(content)