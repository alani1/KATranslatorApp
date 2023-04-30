
from distutils.command.config import config
import os
import re
import csv

import azure.cognitiveservices.speech as speechsdk

import TranslatorApp.Configuration as Configuration
from AIDubbing.BaseSynthesizer import BaseSynthesizer



# Interprets a string as a boolean. Returns True or False
def parseBool(string):
    if type(string) == str:
        if string.lower() == 'true':
            return True
        elif string.lower() == 'false':
            return False
    elif type(string) == bool:
        if string == True:
            return True
        elif string == False:
            return False
    else:
        raise ValueError('Not a valid boolean string')

# Returns a list of dictionaries from a csv file. Where the key is the column name and the value is the value in that column
# The column names are set by the first row of the csv file
def csv_to_dict(csvFilePath):
    with open(csvFilePath, "r", encoding='utf-8-sig') as data:
        entriesDictsList = []
        for line in csv.DictReader(data):
            entriesDictsList.append(line)
    return entriesDictsList

# Returns a list of strings from a txt file. Ignores empty lines and lines that start with '#'
def txt_to_list(txtFilePath):
    with open(txtFilePath, "r", encoding='utf-8-sig') as data:
        entriesList = []
        for line in data:
            if line.strip() != '' and line.strip()[0] != '#':
                entriesList.append(line.strip())
    return entriesList

class AzureSynthesizer(BaseSynthesizer):
    """Merge Subtitles and generate SSML"""

    def __init__(self, YTid, kind="Video", voice=""):
        super().__init__(YTid, kind, voice)

        self.azure_speech_key = Configuration.azure_speech_key
        self.azure_speech_region = Configuration.azure_speech_region

# ======================================== Pronunciation Correction Functions ======================================================
# These functions are used to correct the pronunciation of words that are not pronounced correctly by the Azure Speech Synthesizer
# They modify the SSML text that is sent to the Azure Speech Synthesizer
# ==================================================================================================================================

    interpretAsOverrideFile = os.path.join('SSML_Customization', 'interpret-as.csv')
    interpretAsEntries = csv_to_dict(interpretAsOverrideFile)

    aliasOverrideFile = os.path.join('SSML_Customization', 'aliases.csv')
    aliasEntries = csv_to_dict(aliasOverrideFile)

    urlListFile = os.path.join('SSML_Customization', 'url_list.txt')
    urlList = txt_to_list(urlListFile)

    enWordsFile = os.path.join('SSML_Customization', 'englishWords.txt')
    enWords = txt_to_list(enWordsFile)

    phonemeFile = os.path.join('SSML_Customization', 'Phoneme_Pronunciation.csv')
    phonemeEntries = csv_to_dict(phonemeFile)

    def add_all_pronunciation_overrides(self, text):
        text = self.add_interpretas_tags(text)
        text = self.add_alias_tags(text)
        text = self.add_phoneme_tags(text)

        return text

    def add_interpretas_tags(self, text):
        # Add interpret-as tags from interpret-as.csv
        for entryDict in self.interpretAsEntries:
            # Get entry info
            entryText = entryDict['Text']
            entryInterpretAsType = entryDict['interpret-as Type']
            isCaseSensitive = parseBool(entryDict['Case Sensitive (True/False)'])
            entryFormat = entryDict['Format (Optional)']

            # Create say-as tag
            if entryFormat == "":
                sayAsTagStart = rf'<say-as interpret-as="{entryInterpretAsType}">'
            else:
                sayAsTagStart = rf'<say-as interpret-as="{entryInterpretAsType}" format="{entryFormat}">'
        
            # Find and replace the word
            findWordRegex = rf'(\b["\']?{entryText}[.,!?]?["\']?\b)' # Find the word, with optional punctuation after, and optional quotes before or after
            if isCaseSensitive:
                text = re.sub(findWordRegex, rf'{sayAsTagStart}\1</say-as>', text) # Uses group reference, so remember regex must be in parentheses
            
            else:
                text = re.sub(findWordRegex, rf'{sayAsTagStart}\1</say-as>', text, flags=re.IGNORECASE)

        # Add interpret-as tags from url_list.txt
        for url in self.urlList:
            # This regex expression will match the top level domain extension, and the punctuation before/after it, and any periods, slashes or colons
            # It will then put the say-as characters tag around all matches
            punctuationRegex = re.compile(r'((?:\.[a-z]{2,6}(?:\/|$|\s))|(?:[\.\/:]+))') 
            taggedURL = re.sub(punctuationRegex, r'<say-as interpret-as="characters">\1</say-as>', url)
            # Replace any instances of the URL with the tagged version
            text = text.replace(url, taggedURL)

        # Add interpret-as tags from url_list.txt
        for word in self.enWords:
            # This regex expression will match the top level domain extension, and the punctuation before/after it, and any periods, slashes or colons
            # It will then put the say-as characters tag around all matches
            taggedWord = "<lang xml:lang='en-EN'>%s</lang>" % word
            # Replace any instances of the URL with the tagged version
            text = text.replace(word, taggedWord)


        return text

    def add_alias_tags(self, text):
        for entryDict in self.aliasEntries:
            # Get entry info
            entryText = entryDict['Original Text']
            entryAlias = entryDict['Alias']
            if entryDict['Case Sensitive (True/False)'] == "":
                isCaseSensitive = False
            else:
                isCaseSensitive = parseBool(entryDict['Case Sensitive (True/False)'])

            # Find and replace the word
            findWordRegex = rf'\b["\'()]?{entryText}[.,!?()]?["\']?\b' # Find the word, with optional punctuation after, and optional quotes before or after
            if isCaseSensitive:
                text = re.sub(findWordRegex, rf'{entryAlias}', text)
            else:
                text = re.sub(findWordRegex, rf'{entryAlias}', text, flags=re.IGNORECASE)
        return text


    # Uses the phoneme pronunciation file to add phoneme tags to the text
    def add_phoneme_tags(self, text):
        for entryDict in self.phonemeEntries:
            # Get entry info
            entryText = entryDict['Text']
            entryPhoneme = entryDict['Phonetic Pronunciation']
            entryAlphabet = entryDict['Phonetic Alphabet']

            if entryDict['Case Sensitive (True/False)'] == "":
                isCaseSensitive = False
            else:
                isCaseSensitive = parseBool(entryDict['Case Sensitive (True/False)'])

            # Find and replace the word
            findWordRegex = rf'(\b["\'()]?{entryText}[.,!?()]?["\']?\b)' # Find the word, with optional punctuation after, and optional quotes before or after
            if isCaseSensitive:
                text = re.sub(findWordRegex, rf'<phoneme alphabet="ipa" ph="{entryPhoneme}">\1</phoneme>', text)
            else:
                text = re.sub(findWordRegex, rf'<phoneme alphabet="{entryAlphabet}" ph="{entryPhoneme}">\1</phoneme>', text, flags=re.IGNORECASE)
        return text


# =============================================================================================================================

# ======================================== SRT Subtitle Processing and SSML Generation=========================================
                
    # Generate a SSML string for a subtitle
    # Applies prounciation improvement files
    def generateSSML(self, subtitle):
        # Determine speedFactor value for Azure TTS. It should be either 'default' or a relative change.
        if self.speedFactor == 1.0:
            rate = ''
        else:
            # Whether to add a plus sign to the number to relative change. A negative will automatically be added
            if self.speedFactor >= 1.0:
                percentSign = '+'
            else:
                percentSign = ''
            # Convert speedFactor float value to a relative percentage    
            rate = "rate='" + percentSign + str(round((self.speedFactor - 1.0) * 100, 5)) + "%'"

        # Create string for sentence pauses, if not default
        if not self.azureSentencePause == 'default' and self.azureSentencePause.isnumeric():
            pauseTag = f'<mstts:silence type="Sentenceboundary-exact" value="{self.azureSentencePause}ms"/>'
        else:
            pauseTag = ''
    
        # Process text using pronunciation customization set by user
        text = self.add_all_pronunciation_overrides(subtitle['content'])

        # Create SSML syntax for Azure TTS
        ssml = f"<speak version='1.0' xml:lang='en-US' xmlns='http://www.w3.org/2001/10/synthesis' " \
            "xmlns:mstts='http://www.w3.org/2001/mstts'>" \
            f"<voice name='{self.voiceName}'>{pauseTag}" \
            f"<lang xml:lang='{self.languageCode}'>" \
            f"<prosody {rate}>{text}</prosody></lang></voice></speak>"

        return ssml

# =============================================================================================================================

# ======================================== Audio Synthesizing and processing ==================================================

    # Synthesize a Single Subtilte section using Azure TTS
    def synthesizeSingleSubtitle(self, subtitle, filePath):

        print("Synthesizing Audio for %s" % filePath)

        speech_config = speechsdk.SpeechConfig(subscription=self.azure_speech_key, region=self.azure_speech_region)
        # For Azure voices, see: https://learn.microsoft.com/en-us/azure/cognitive-services/speech-service/language-support?tabs=stt-tts
        speech_config.speech_synthesis_voice_name=self.voiceName
        # For audio outputs, see: https://learn.microsoft.com/en-us/python/api/azure-cognitiveservices-speech/azure.cognitiveservices.speech.speechsynthesisoutputformat?view=azure-python
        speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio48Khz192KBitRateMonoMp3)
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

        #GenerateSSML
        subtitle['ssml'] = self.generateSSML(subtitle)
        print("\nStart: %s, End: %s, Rate: %s char/s" % (subtitle['start'], subtitle['end'], subtitle['char_rate']))
        print("SUBTITLE:\n" + subtitle['content'])
        print("SSML:\n" + subtitle['ssml'])

        #result = synthesizer.speak_text_async(text).get()
        result = synthesizer.speak_ssml_async(subtitle['ssml']).get()
    
        stream = speechsdk.AudioDataStream(result)

        # Save to file using save_to_wav_file method of audio object
        stream.save_to_wav_file(filePath)

        return stream

# =============================================================================================================================


    




