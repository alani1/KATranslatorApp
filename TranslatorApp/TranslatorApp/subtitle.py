import json
from datetime import datetime
from flask import (
    Blueprint, flash, g, redirect, render_template, make_response, request, jsonify
)
import requests
from TranslatorApp import Configuration


def jprint(obj):
        text = json.dumps(obj, sort_keys=True, indent=4)
        return text

def getAmaraEditorLink(amaraID):
    return '<a target=_new href="https://amara.org/subtitles/editor/' + amaraID + '/de?team=khan-academy">Link to Amara Editor</a><p/>' + '<a target=_new href="https://amara.org/teams/khan-academy/videos/' + amaraID + '/collaborations/">Amara assignment (for admins)</a><p/>'

def getAmaraVideoLink(amaraID):
    return '<a target=_new href="https://amara.org/en/videos/' + amaraID + '/de?team=khan-academy">Link to Amara Video</a>'


class Subtitles(object):

    deeplAPI = Configuration.deeplAPI

    def __init__(self, YTid = ""):
        self.YTid = ""
        self.amaraAPI = ""
        self.amaraID = ""
        self.force = False
        self.subtitleInfo = ""
        self.enSubtitle = ""
        self.translationStep = 0
        self.message = "what is the message123??"

        if len(YTid) > 0:
            self.YTid = YTid

        if 'YTid' in request.form:
            self.YTid = request.form['YTid']

        amaraAPI = request.cookies.get('amaraAPI')
        if (amaraAPI):
            self.amaraAPI = amaraAPI

        if 'amaraAPI' in request.form:
            self.amaraAPI = request.form['amaraAPI']

        if 'force' in request.form:
            self.message = "may the force be with you"
            self.force = request.form['force']


    def updateVideoStatus(self,status):
        var = ""


    def checkSTStep(self, amaraID):
        self.amaraID = amaraID

        url = "https://amara.org/api/teams/khan-academy/subtitle-requests/?language=de&video=" + self.amaraID
        print(url)
        headers = {'X-api-key': self.amaraAPI} 
        print(headers)
        response = requests.get(url,headers=headers).json()

        
        if( response.get('objects') != None and len(response['objects']) > 0):
            status = response['objects'][0]['work_status']
            subtitler = response['objects'][0]['subtitler']

            #TODO improve: check if subtitle request is assigned to me (AMARA UserID), MetaDataField: googleplus
            if (status == "being-subtitled"):

                #Subtitle is in progress on Amara, update the status in DB
                self.updateVideoStatus("Assigned")

                #Check if we are in Step 3 e.g. are there already translated Versions of the subtitle
                if ( self.hasGermanSubtitles()):

                    #TODO: check if Step 4 is finished e.g. has the subtitle been marked as complete in our DataBase or on Amara --> udpateDB ???
                    result = { 'result': 3 }
                else:
                    result = { 'result': 2 }
            else:
                result = { 'result': 1 }
        else:
            result = { 'result': 1 }
    
        return jsonify(result)

    def hasGermanSubtitles(self):

        subInfoURL = "https://amara.org/api/videos/" + self.amaraID + "/languages/de"
        headers = {'X-api-key': self.amaraAPI} 
        subResult = requests.get(subInfoURL,headers=headers)
        print(subInfoURL)
        print("hasGermanSubtitles");
                            
        if subResult.status_code == 403:
            self.message = "Please add your Amara API Key, which you can find in your <a target=_new href='https://amara.org/profiles/account'>Amara Account Profile</a>"
            self.translationStep = 1
            return False

        subInfo = subResult.json()
        print(subInfo["subtitles_complete"])
        print(len(subInfo["versions"]))
                         
        if ( subInfo["subtitles_complete"] or len(subInfo["versions"]) > 0 ):
            print("True")
            self.message = "This Subtitle has already been translated to German"
            self.translationStep = 4
            return True
        else:
            return False


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
            amaraAPI=self.amaraAPI,
            amaraID=self.amaraID,
            translationStep=self.translationStep,
            amaraEditorLink=getAmaraEditorLink(self.amaraID),
            baseURL=Configuration.baseURL,
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
        
        #make this more robust to handle when no result is found
        if ( response["meta"]["total_count"] > 0 and response.get('objects') != None and len(response['objects']) > 0):
            #iterate as there may be multiple IDs and find the khan-academy team
            
            for vid in response['objects']:
                amaraID = vid['id']
                self.amaraID = amaraID;

                title = vid['title']
                description = vid['description']

                #get the English subtitle if it is empty to avoid repeated calls
                if ( not self.enSubtitle is object):
                    ensubURL = "https://amara.org/api/videos/" + amaraID + "/languages/en/subtitles/?format=txt"
                    self.enSubtitle = requests.get(ensubURL)


                    self.subtitleInfo = "<table class='table'><tr><td>Translating Video</td><td><b>" + title + "</b></td></tr>" \
                    "<tr><td># Characters</td><td>" + str(len(title)+len(description)+len(self.enSubtitle.content)) + '</td></tr>' \
                    "<tr><td>Deepl Chars Left</td><td>" + self.getDeeplUsage() +"</td></tr>" \
                    "<tr><td>Amara ID</td><td>" + amaraID + "</td></tr></table>"

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
                                self.translationStep = 1
                                return "check message"

                            subInfo = subResult.json()
                         
                            if ( not subInfo["subtitles_complete"] ):
                                return self.translateSubtitleAndSubmit(self.enSubtitle, vid, subInfo["published"], subInfo["subtitle_count"])        

                            else:
                                self.message = "This Subtitle has already been translated to German"
                                self.translationStep = 4
                                return ""
                
                    return self.translateSubtitleAndSubmit(self.enSubtitle, vid, False, 0)

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
                    self.translationStep = 4
                else:
                    self.message = "Error in translation" + result.content()


            else:
                self.message = "<b>There are already versions of this Video, please Review, Edit and Publish</b>" 
                self.translationStep = 4
        else:
            self.message = '<b>Please Assign this Video to yourself by clicking on Translate Button<br/>' + str(getAmaraVideoLink(amaraID))  
            self.translationStep = 2


#TODO: Load AmaraUserID from UserDatabase
def getAmaraUserID():
    return ""


bp = Blueprint('Subtitles', __name__, url_prefix='/subtitles')

@bp.after_request 
def after_request(response):
    header = response.headers
    header['Access-Control-Allow-Origin'] = '*'
    # Other headers can be added here if needed
    return response

@bp.route('/checkSTStep', methods = ['GET', 'POST'])
def checkSTStep():

    amaraAPI = ""
    amaraID = ""
    if 'a' in request.args:
        amaraAPI = request.args.get('a')
        
    if 'id' in request.args:
        amaraID = request.args.get('id')

    if (amaraAPI == "" or amaraID == ""):
        return "Error"
    else:

        st = Subtitles()
        st.amaraAPI = amaraAPI
        return st.checkSTStep(amaraID)

@bp.route('/', methods = ['GET', 'POST'])
@bp.route('/<YTid>', methods = ['GET', 'POST'])
def subtitles(YTid=""):

    #Create Blueprint Object
    st = Subtitles(YTid)
    return st.render()


