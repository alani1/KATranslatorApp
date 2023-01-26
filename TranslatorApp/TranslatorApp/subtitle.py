import json
from datetime import datetime
from flask import (
    Blueprint, flash, g, redirect, render_template, make_response, request, session, url_for
)
import requests
from TranslatorApp import Configuration


def jprint(obj):
        text = json.dumps(obj, sort_keys=True, indent=4)
        return text

def getAmaraEditorLink(amaraID):
    return '<a target=_new href="https://amara.org/subtitles/editor/' + amaraID + '/de?team=khan-academy">Link to Amara Editor</a><p/>'

def getAmaraVideoLink(amaraID):
    return '<a target=_new href="https://amara.org/en/videos/' + amaraID + '/de?team=khan-academy">Link to Amara Video</a>'


bp = Blueprint('Subtitles', __name__, url_prefix='/subtitles')


class Subtitles(object):

    deeplAPI = Configuration.deeplAPI

    def __init__(self, YTid = ""):
        self.YTid = ""
        self.amaraAPI = ""
        self.force = False
        self.subtitleInfo = ""
        self.message = "what is the message123??"

        if len(YTid) > 0:
            self.YTid = YTid

        if 'YTid' in request.form:
            self.YTid = request.form['YTid']

        amaraAPI = request.cookies.get('amaraAPI')
        if (amaraAPI):
            print("cookie: " + amaraAPI)
            self.amaraAPI = amaraAPI

        if 'amaraAPI' in request.form:
            self.amaraAPI = request.form['amaraAPI']

        if 'force' in request.form:
            self.message = "may the force be with you"
            self.force = request.form['force']

    def render(self):
        
        if len(self.YTid) > 0:
            self.getEnglishSubtitle()
        else:
            self.message = "Please enter a Youtube ID and your Amara API Key to translate"
    
        resp = make_response(render_template(
            'subtitle.html',
            title='Subtitle Translator',
            year=datetime.now().year,
            message=self.message,
            subtitleInfo=self.subtitleInfo,
            YTid=self.YTid,
            amaraAPI=self.amaraAPI
        ))


        if len(self.amaraAPI) > 0:
            resp.set_cookie('amaraAPI', self.amaraAPI)
    
        return resp


    def getDeeplUsage(self):

        url = "https://api-free.deepl.com/v2/usage"
        headers = { 'Authorization': 'DeepL-Auth-Key ' + self.deeplAPI }
        result = requests.get(url,headers=headers)

        result = result.json()
        return str(result["character_limit"] - result["character_count"])

    def deeplTranslate(self, content):

        url = "https://api-free.deepl.com/v2/translate"
        headers = { 'Authorization': 'DeepL-Auth-Key '+ self.deeplAPI }
        data = {
            'target_lang': 'DE',
            'formality': 'less',
            'text': content
        }
        result = requests.post(url,headers=headers, data=data)

        return result

    def addNewSubtitle(self, amaraID, subtitle, title, description):
        url = "https://amara.org/api/videos/" + amaraID + "/languages/de/subtitles/"
        headers = {'X-api-key': self.amaraAPI} 

        data = {
            'sub_format': 'txt',
            'title': title,
            'description': description,
            'subtitles': subtitle,
            'action': 'save-draft',
            'team': 'khan-academy'
        }
        result = requests.post(url,headers=headers,data=data)
        #403 is forbiddeen
        if (result):
            return subtitle
        elif result.status_code == 403: #Forbidden
            self.message = "403: Access to this Subtitle is Forbidden for you. Maybe the subtitle is assigned to someone else already<br/>" + str(result.text) + str(getAmaraEditorLink(amaraID))
            return ""
        else:
            return str(result.status_code)

    def isAssignedToMe(self, amaraID):
        url = "https://amara.org/api/videos/" + amaraID + "/languages/de/subtitles/actions"
        headers = {'X-api-key': self.amaraAPI} 
        result = requests.get(url,headers=headers)

        if result.status_code == 200:
            return True
        else:
            return False

    #Download the English Subtitle based on YoutTubeID
    def getEnglishSubtitle(self):
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
                title = vid['title']
                description = vid['description']

                #get the English subtitle
                ensubURL = "https://amara.org/api/videos/" + amaraID + "/languages/en/subtitles/?format=txt"
                enSubtitle = requests.get(ensubURL)

                self.subtitleInfo = "<table class='table'><tr><td>Translating Video</td><td><b>" + title + "</b></td></tr>" \
                "<tr><td># Characters</td><td>" + str(len(title)+len(description)+len(enSubtitle.content)) + '</td></tr>' \
                "<tr><td>Deepl Chars Left</td><td>" + self.getDeeplUsage() +"</td></tr>" \
                "<tr><td>Amara ID</td><td>" + amaraID + "</td></tr></table>" + getAmaraEditorLink(amaraID)

                #Select only Videos from Team Khan-Academy 
                if (vid['team'] == "khan-academy"):
              
                    ret = ""
                    for lang in vid['languages']:
                        if lang['name'] == "German":

                            #Found a German Language for the selected Video
                            #Get detailed information on German Subtitle & check if it is completed
                            subInfoURL = "https://amara.org/api/videos/" + amaraID + "/languages/de"
                            headers = {'X-api-key': self.amaraAPI} 
                            subResult = requests.get(subInfoURL,headers=headers)
                            
                            if subResult.status_code == 403:
                                self.message = "Please add your Amara API Key, which you can find in your <a target=_new href='https://amara.org/profiles/account'>Amara Account Profile</a>"
                                return "check message"

                            subInfo = subResult.json()
                         
                            if ( not subInfo["subtitles_complete"] ):
                                return self.translateSubtitleAndSubmit(enSubtitle, vid, subInfo["published"], subInfo["subtitle_count"])        

                            else:
                                self.message = "This Subtitle has already been translated to German"
                                return ""
                
                    return self.translateSubtitleAndSubmit(enSubtitle, vid, False, 0)

            self.message = "<b>Error, Khan Academy Team not found," + amaraID

        else:
            self.message = "<b>Unknown Video</b><br/>Youtube Video could not be found on amara.org"

    def translateSubtitleAndSubmit(self, enSubtitle, vid, published, subtitle_count):
        amaraID = vid['id']
        title = vid['title']
        description = vid['description']

        #check if this is assigned to myself
        if self.isAssignedToMe(amaraID):
        
            if self.force or (not published and subtitle_count == 0):
 
                result = self.deeplTranslate(enSubtitle.content)

                if result:
                    #return jprint(result.json())
                    deSubtitle = result.json()["translations"][0]["text"]

                    deTitle = self.deeplTranslate(title).json()["translations"][0]["text"]
                    deDescription = self.deeplTranslate(description).json()["translations"][0]["text"]

                    result = self.addNewSubtitle(amaraID, deSubtitle, deTitle, deDescription)
                    self.message = "Sucessfully translated. Change to Amara Tab to Review, Edit and Publish"
                else:
                    self.message = "Error in translation" + result.content()


            else:
                self.message = "<b>There are already versions of this Video, please Review, Edit and Publish</b>" 
        else:
            self.message = '<b>Please Assign this Video to yourself by clicking on Translate Button<br/>' + str(getAmaraVideoLink(amaraID))  


@bp.route('/', methods = ['GET', 'POST'])
@bp.route('/<YTid>', methods = ['GET', 'POST'])
def subtitles(YTid=""):

    #Create Blueprint Object
    st = Subtitles(YTid)
    return st.render()
