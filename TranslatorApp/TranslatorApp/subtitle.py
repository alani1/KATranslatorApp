import json
import re
from datetime import datetime
from flask import (
    Blueprint, flash, g, redirect, render_template, make_response, request, jsonify, Response
)
import requests
from TranslatorApp import Configuration
import pymysql

# Timeout (seconds) for all outbound HTTP requests to Amara and DeepL APIs
API_TIMEOUT = 30


def jprint(obj):
    """Pretty-print a JSON-serializable object."""
    return json.dumps(obj, sort_keys=True, indent=4)

def getAmaraEditorLink(amaraID):
    return '<a target=_new href="https://amara.org/subtitles/editor/' + amaraID + '/de?team=khan-academy">Link to Amara Editor</a><p/>' + '<a target=_new href="https://amara.org/teams/khan-academy/videos/' + amaraID + '/collaborations/">Amara assignment (for admins)</a><p/>'

def getAmaraVideoLink(amaraID):
    return '<a target=_new href="https://amara.org/en/videos/' + amaraID + '/de?team=khan-academy">Link to Amara Video</a>'


class Subtitles(object):

    deeplAPI = Configuration.deeplAPI

    def __init__(self, YTid=""):
        self.YTid = ""
        self.amaraAPI = ""
        self.amaraID = ""
        self.force = False
        self.subtitleInfo = ""
        self.enSubtitle = ""       # Will become a requests.Response once fetched
        self.translationStep = 0
        self.message = ""

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
            self.force = request.form['force']
            print(f"[SUBTITLE] Force flag set to: {self.force}")


    def connectDB(self):
        # Connect to the database
        self.dbConnection = pymysql.connect(host=Configuration.dbHost,
                    user=Configuration.dbUser,
                    password=Configuration.dbPassword,
                    db=Configuration.dbDatabase,
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor)

    def getDBUserName(self, amaraUser):
        """Look up the WordPress username for a given Amara user via the usermeta 'googleplus' field."""
        sql = (
            "SELECT wp_users.user_login AS user "
            "FROM wp_users "
            "INNER JOIN wp_usermeta ON wp_usermeta.user_id = wp_users.ID "
            "WHERE wp_usermeta.meta_key = 'googleplus' AND wp_usermeta.meta_value = %s"
        )
        cursor = self.dbConnection.cursor()
        cursor.execute(sql, (amaraUser,))
        result = cursor.fetchall()
        if len(result) > 0:
            return result[0]['user']
        return amaraUser

    def updateVideoStatus(self, stRequest):
        """Update translation status in the DB based on the Amara subtitle request state."""
        self.connectDB()
        try:
            # TODO: Check if user is allowed to update (e.g. Contributor role)
            status = stRequest['work_status']
            translator = self.getDBUserName(stRequest['subtitler']['username'])

            cursor = self.dbConnection.cursor()

            # Fetch current record
            sql = "SELECT * FROM `ka-content` WHERE youtube_id = %s"
            cursor.execute(sql, (self.YTid,))
            result = cursor.fetchall()
            if len(result) == 0:
                print(f"[SUBTITLE] ERROR: No DB record found for youtube_id={self.YTid}")
                return

            current = result[0]

            # Determine which fields to update
            update_fields = {}

            # Always update when status is empty
            if current['translation_status'] is None:
                update_fields['translator'] = translator
                if status == 'being-subtitled':
                    update_fields['translation_status'] = 'Assigned'
                elif status in ('needs-reviewer', 'beeing-reviewed'):
                    update_fields['translation_status'] = 'Translated'
                update_fields['translation_date'] = datetime.today().strftime("%Y-%m-%d")

            # Assigned -> Translated (already in review)
            if status in ('needs-reviewer', 'beeing-reviewed') and current['translation_status'] == 'Assigned':
                update_fields['translator'] = translator
                update_fields['translation_status'] = 'Translated'
                update_fields['translation_date'] = datetime.today().strftime("%Y-%m-%d")

            # Translated -> Approved (complete)
            if status == 'complete' and current['translation_status'] in ('Assigned', 'Translated'):
                update_fields['translation_status'] = 'Approved'

            if not update_fields:
                return

            # Build parameterized UPDATE
            set_clause = ', '.join([f"`{k}` = %s" for k in update_fields])
            values = list(update_fields.values())
            values.extend([self.YTid, translator])
            sql = f"UPDATE `ka-content` SET {set_clause} WHERE youtube_id = %s AND (translator IS NULL OR translator = %s)"

            cursor.execute(sql, tuple(values))
            self.dbConnection.commit()
        finally:
            self.dbConnection.close()



    def checkSTStep(self):
        """Determine which workflow step the subtitle is at on Amara."""
        url = "https://amara.org/api/teams/khan-academy/subtitle-requests/?language=de&video=" + self.amaraID
        print(url)
        headers = {'X-api-key': self.amaraAPI}
        response = requests.get(url, headers=headers, timeout=API_TIMEOUT).json()

        if( response.get('objects') != None and len(response['objects']) > 0):
            status = response['objects'][0]['work_status']


            #TODO improve: check if subtitle request is assigned to me (AMARA UserID), MetaDataField: googleplus
            if (status == "being-subtitled"):

                #Subtitle is in progress on Amara, update the status in DB
                self.updateVideoStatus(response['objects'][0])

                #Check if we are in Step 3 e.g. are there already translated Versions of the subtitle
                if ( self.hasGermanSubtitles()):

                    #TODO: check if Step 4 is finished e.g. has the subtitle been marked as complete in our DataBase or on Amara --> udpateDB ???
                    result = { 'result': 3 }
                else:
                    result = { 'result': 2 }
            elif (status == "needs-reviewer" or status == 'beeing-reviewed'):
                #Subtitle is in progress on Amara, update the status in DB
                self.updateVideoStatus(response['objects'][0])

                result = { 'result': 4 }
            elif (status == "complete"):
                #Subtitle is in progress on Amara, update the status in DB
                self.updateVideoStatus(response['objects'][0])

                result = { 'result': 5 }
            else:
                result = { 'result': 1 }
        else:
            result = { 'result': 1 }
    
        return jsonify(result)

    def hasGermanSubtitles(self):
        """Check whether any German subtitle version already exists on Amara."""
        subInfoURL = "https://amara.org/api/videos/" + self.amaraID + "/languages/de"
        headers = {'X-api-key': self.amaraAPI}
        subResult = requests.get(subInfoURL, headers=headers, timeout=API_TIMEOUT)
        print(f"[SUBTITLE] hasGermanSubtitles: {subInfoURL}")
                            
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
        """Build and return the full subtitle page response."""
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
            resp.set_cookie('amaraAPI', self.amaraAPI, httponly=True, samesite='Lax')
    
        return resp


    def getDeeplUsage(self):
        """Return remaining DeepL character quota as a string."""
        url = "https://api-free.deepl.com/v2/usage"
        headers = {'Authorization': 'DeepL-Auth-Key ' + self.deeplAPI}
        result = requests.get(url, headers=headers, timeout=API_TIMEOUT)
        data = result.json()
        return str(data["character_limit"] - data["character_count"])

    def deeplTranslate(self, content):
        """Send text to DeepL for EN->DE translation. Returns the raw requests.Response."""
        url = "https://api-free.deepl.com/v2/translate"
        headers = {'Authorization': 'DeepL-Auth-Key ' + self.deeplAPI}
        data = {
            'target_lang': 'DE',
            'formality': 'less',
            'text': content
        }
        result = requests.post(url, headers=headers, data=data, timeout=API_TIMEOUT)
        return result

    def translateSRT(self, srt_text):
        """Translate an SRT string cue-by-cue, preserving all timing and cue numbering."""
        # Normalize line endings (Amara returns \r\n on Windows; must be \n for reliable splitting)
        srt_text = srt_text.replace('\r\n', '\n').replace('\r', '\n')
        blocks = re.split(r'\n\n+', srt_text.strip())
        print(f"[SUBTITLE] translateSRT: {len(blocks)} cue blocks found")
        if len(blocks) > 0:
            print(f"[SUBTITLE] First block preview: {blocks[0][:120]}")
        translated_blocks = []

        for i, block in enumerate(blocks):
            lines = block.split('\n')
            if len(lines) < 3:
                # Keep malformed or empty blocks as-is
                print(f"[SUBTITLE] Block {i}: skipped (only {len(lines)} lines)")
                translated_blocks.append(block)
                continue

            index = lines[0]       # cue number, e.g. "1"
            timecode = lines[1]    # e.g. "00:00:01,000 --> 00:00:03,000"
            cue_text = '\n'.join(lines[2:])  # may be multi-line within one cue

            result = self.deeplTranslate(cue_text)
            if not result:
                print(f"[SUBTITLE] Block {i}: DeepL returned no result")
                return None

            translated_text = result.json()["translations"][0]["text"]
            translated_blocks.append(f"{index}\n{timecode}\n{translated_text}")
            print(f"[SUBTITLE] Block {i}/{len(blocks)}: translated OK")

        if len(translated_blocks) != len(blocks):
            raise RuntimeError(
                f"Cue boundary violation: input={len(blocks)} output={len(translated_blocks)}"
            )

        print(f"[SUBTITLE] translateSRT: all {len(translated_blocks)} blocks translated")
        return '\n\n'.join(translated_blocks)

    def translateSRT_streaming(self, srt_text):
        """Generator that translates SRT cue-by-cue, yielding SSE progress events.
        Final event contains the complete translated SRT or an error."""
        srt_text = srt_text.replace('\r\n', '\n').replace('\r', '\n')
        blocks = re.split(r'\n\n+', srt_text.strip())
        total = len(blocks)
        print(f"[SUBTITLE] translateSRT_streaming: {total} cue blocks found")
        translated_blocks = []

        for i, block in enumerate(blocks):
            lines = block.split('\n')
            if len(lines) < 3:
                translated_blocks.append(block)
                yield f"data: {json.dumps({'cue': i + 1, 'total': total, 'status': 'skip'})}\n\n"
                continue

            index = lines[0]
            timecode = lines[1]
            cue_text = '\n'.join(lines[2:])

            try:
                result = self.deeplTranslate(cue_text)
                if not result:
                    yield f"data: {json.dumps({'error': f'DeepL returned no result for cue {i + 1}'})}\n\n"
                    return
                translated_text = result.json()["translations"][0]["text"]
            except Exception as e:
                yield f"data: {json.dumps({'error': f'DeepL error on cue {i + 1}: {str(e)}'})}\n\n"
                return

            translated_blocks.append(f"{index}\n{timecode}\n{translated_text}")
            yield f"data: {json.dumps({'cue': i + 1, 'total': total, 'status': 'ok'})}\n\n"

        full_srt = '\n\n'.join(translated_blocks)
        yield f"data: {json.dumps({'cue': total, 'total': total, 'status': 'translating_meta'})}\n\n"
        # Store the translated SRT for use by the route handler
        self._translated_srt = full_srt
        yield f"data: {json.dumps({'status': 'srt_done', 'total': total})}\n\n"

    def addNewSubtitle(self, amaraID, subtitle, title, description):
        """Upload translated SRT subtitles to Amara as a draft."""
        url = "https://amara.org/api/videos/" + amaraID + "/languages/de/subtitles/"
        headers = {'X-api-key': self.amaraAPI}

        data = {
            'sub_format': 'srt',
            'title': title,
            'description': description,
            'subtitles': subtitle,
            'action': 'save-draft',
            'team': 'khan-academy'
        }
        result = requests.post(url, headers=headers, data=data, timeout=API_TIMEOUT)
        print(f"[SUBTITLE] addNewSubtitle response: {result.status_code}")
        if (result):
            return subtitle
        elif result.status_code == 403: #Forbidden
            self.message = "403: Access to this Subtitle is Forbidden for you. Maybe the subtitle is assigned to someone else already<br/>" + str(result.text) + str(getAmaraEditorLink(amaraID))
            print(f"[SUBTITLE] Upload FAILED: 403 Forbidden")
            return ""
        else:
            print(f"[SUBTITLE] Upload FAILED: {result.status_code} - {result.text[:200]}")
            return str(result.status_code)

    def isAssignedToMe(self, amaraID):
        """Check if the current user has subtitle actions available (i.e. is assigned)."""
        url = "https://amara.org/api/videos/" + amaraID + "/languages/de/subtitles/actions"
        headers = {'X-api-key': self.amaraAPI}
        result = requests.get(url, headers=headers, timeout=API_TIMEOUT)
        return result.status_code == 200

    # Download the English subtitle based on YouTube ID
    def getEnglishSubtitle(self):
        """Resolve YouTube ID -> Amara video -> fetch English SRT -> trigger translation."""
        url = "https://amara.org/api/videos/?video_url=https://www.youtube.com/watch?v=" + self.YTid
        headers = {'X-api-key': self.amaraAPI}
        response = requests.get(url, headers=headers, timeout=API_TIMEOUT).json()
        
        #make this more robust to handle when no result is found
        if ( response["meta"]["total_count"] > 0 and response.get('objects') != None and len(response['objects']) > 0):
            #iterate as there may be multiple IDs and find the khan-academy team
            
            for vid in response['objects']:
                amaraID = vid['id']
                self.amaraID = amaraID;

                title = vid['title']
                description = vid['description']

                #get the English subtitle if it is empty to avoid repeated calls
                if isinstance(self.enSubtitle, str):
                    ensubURL = "https://amara.org/api/videos/" + amaraID + "/languages/en/subtitles/?format=srt"
                    print(f"[SUBTITLE] Fetching English SRT from: {ensubURL}")
                    self.enSubtitle = requests.get(ensubURL, timeout=API_TIMEOUT)
                    print(f"[SUBTITLE] English SRT response: {self.enSubtitle.status_code}, length={len(self.enSubtitle.text)}")

                    self.subtitleInfo = (
                        "<table class='table'>"
                        f"<tr><td>Translating Video</td><td><b>{title}</b></td></tr>"
                        f"<tr><td># Characters</td><td>{len(title) + len(description) + len(self.enSubtitle.text)}</td></tr>"
                        f"<tr><td>DeepL Chars Left</td><td>{self.getDeeplUsage()}</td></tr>"
                        f"<tr><td>Amara ID</td><td>{amaraID}</td></tr>"
                        "</table>"
                    )

                #Select only videos from Team Khan-Academy
                if vid['team'] == "khan-academy":

                    for lang in vid['languages']:
                        if lang['name'] == "German":

                            # Found a German language — check completion status
                            subInfoURL = "https://amara.org/api/videos/" + amaraID + "/languages/de"
                            headers = {'X-api-key': self.amaraAPI}
                            subResult = requests.get(subInfoURL, headers=headers, timeout=API_TIMEOUT)
                            
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
        """Check eligibility and signal step 3 (ready to translate via SSE) instead of blocking."""
        amaraID = vid['id']

        print(f"[SUBTITLE] translateSubtitleAndSubmit: force={self.force}, published={published}, subtitle_count={subtitle_count}")

        # Check if this is assigned to myself
        assigned = self.isAssignedToMe(amaraID)
        print(f"[SUBTITLE] isAssignedToMe({amaraID}): {assigned}")
        if assigned:
            if self.force or (not published and subtitle_count == 0):
                # Signal step 3: page will render immediately, JS auto-starts SSE stream
                print(f"[SUBTITLE] Ready to translate — deferring to SSE stream (step 3)")
                self.message = "Translation ready — starting automatically..."
                self.translationStep = 3
            else:
                self.message = "<b>There are already versions of this Video, please Review, Edit and Publish</b>"
                self.translationStep = 4
        else:
            self.message = '<b>Please Assign this Video to yourself by clicking on translate link</b><br/>' + str(getAmaraVideoLink(amaraID))
            self.translationStep = 2


#TODO: Load AmaraUserID from UserDatabase
def getAmaraUserID():
    return ""


bp = Blueprint('Subtitles', __name__, url_prefix='/subtitles')

@bp.after_request
def after_request(response):
    """Set security and caching headers on every response."""
    # TODO: Restrict CORS to your actual frontend origin instead of wildcard
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    return response

@bp.route('/checkSTStep', methods = ['GET', 'POST'])
def checkSTStep():
    st = Subtitles()

    amaraAPI = ""
    amaraID = ""
    if 'a' in request.args:
        st.amaraAPI = request.args.get('a')
        
    if 'id' in request.args:
        st.amaraID = request.args.get('id')

    if 'YTid' in request.args:
        st.YTid = request.args.get('YTid')

    if (st.amaraAPI == "" or st.amaraID == ""):
        return "Error"
    else:
        return st.checkSTStep()

@bp.route('/', methods = ['GET', 'POST'])
@bp.route('/<YTid>', methods = ['GET', 'POST'])
def subtitles(YTid=""):

    #Create Blueprint Object
    st = Subtitles(YTid)
    return st.render()


@bp.route('/translate-stream')
def translate_stream():
    """SSE endpoint that streams translation progress per cue, then uploads to Amara."""
    amaraAPI = request.args.get('a', '')
    YTid = request.args.get('YTid', '')
    force = request.args.get('force', '') == '1'

    if not amaraAPI or not YTid:
        return jsonify({'error': 'Missing amaraAPI or YTid'}), 400

    def generate():
        # Create a minimal Subtitles instance outside of request.form context
        st = Subtitles.__new__(Subtitles)
        st.YTid = YTid
        st.amaraAPI = amaraAPI
        st.amaraID = ''
        st.force = force
        st.subtitleInfo = ''
        st.enSubtitle = ''
        st.translationStep = 0
        st.message = ''
        st.deeplAPI = Configuration.deeplAPI

        yield f"data: {json.dumps({'status': 'init', 'message': 'Resolving video on Amara...'})}\n\n"

        # 1. Resolve YouTube ID to Amara video
        try:
            url = "https://amara.org/api/videos/?video_url=https://www.youtube.com/watch?v=" + YTid
            headers = {'X-api-key': amaraAPI}
            response = requests.get(url, headers=headers, timeout=API_TIMEOUT).json()
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Failed to reach Amara: {str(e)}'})}\n\n"
            return

        if response["meta"]["total_count"] == 0 or not response.get('objects'):
            yield f"data: {json.dumps({'error': 'Video not found on Amara'})}\n\n"
            return

        vid = None
        for v in response['objects']:
            if v.get('team') == 'khan-academy':
                vid = v
                break
        if not vid:
            yield f"data: {json.dumps({'error': 'Khan Academy team video not found'})}\n\n"
            return

        amaraID = vid['id']
        st.amaraID = amaraID
        title = vid['title']
        description = vid['description']

        yield f"data: {json.dumps({'status': 'init', 'message': f'Found video: {title}'})}\n\n"

        # 2. Check assignment
        if not st.isAssignedToMe(amaraID):
            yield f"data: {json.dumps({'error': 'Video is not assigned to you. Please assign it first.'})}\n\n"
            return

        # 3. Fetch English SRT
        yield f"data: {json.dumps({'status': 'init', 'message': 'Downloading English subtitles...'})}\n\n"
        try:
            ensubURL = f"https://amara.org/api/videos/{amaraID}/languages/en/subtitles/?format=srt"
            enSubtitle = requests.get(ensubURL, timeout=API_TIMEOUT)
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Failed to fetch English SRT: {str(e)}'})}\n\n"
            return

        if enSubtitle.status_code != 200:
            yield f"data: {json.dumps({'error': f'English SRT not available (HTTP {enSubtitle.status_code})'})}\n\n"
            return

        # 4. Stream translation progress
        yield f"data: {json.dumps({'status': 'translating', 'message': 'Translating subtitles...'})}\n\n"
        for event in st.translateSRT_streaming(enSubtitle.text):
            yield event

        if not hasattr(st, '_translated_srt') or not st._translated_srt:
            # Error was already yielded inside the generator
            return

        # 5. Translate title & description
        yield f"data: {json.dumps({'status': 'translating_meta', 'message': 'Translating title & description...'})}\n\n"
        try:
            deTitle = st.deeplTranslate(title).json()["translations"][0]["text"]
            deDescription = st.deeplTranslate(description).json()["translations"][0]["text"]
            deDescription = deDescription.replace("https://www.khanacademy.org", "https://de.khanacademy.org")
            deDescription += "\n\nDie deutschen Untertitel für dieses Video wurden vom Team KA Deutsch e.V. erstellt. Wir brauchen deine Unterstützung. https://www.kadeutsch.org"
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Failed to translate title/description: {str(e)}'})}\n\n"
            return

        # 6. Upload to Amara
        yield f"data: {json.dumps({'status': 'uploading', 'message': 'Uploading to Amara...'})}\n\n"
        result = st.addNewSubtitle(amaraID, st._translated_srt, deTitle, deDescription)

        if result and result == st._translated_srt:
            yield f"data: {json.dumps({'status': 'done', 'message': 'Successfully translated and uploaded! Switch to Amara to review.'})}\n\n"
        elif result == '':
            yield f"data: {json.dumps({'error': '403 Forbidden — subtitle may be assigned to someone else'})}\n\n"
        else:
            yield f"data: {json.dumps({'error': f'Upload failed with status: {result}'})}\n\n"

    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
    })


