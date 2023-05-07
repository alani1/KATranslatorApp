
from distutils.command.config import config
import os
import re
import csv

from elevenlabslib import *
from elevenlabslib.helpers import *

import TranslatorApp.Configuration as Configuration
from AIDubbing.BaseSynthesizer import BaseSynthesizer




class ElevenLabSynthesizer(BaseSynthesizer):
    """Generate WAV with ElevenLab"""

    def __init__(self, YTid, kind, args):
        super().__init__(YTid, kind, args)
# ======================================== Audio Synthesizing and processing ==================================================

    #ElevenLabs Multilingual Model cannot properly spell numbers, so we need to do it ourselves
    def spellNumberGerman(self,number):
        # create a list of the German words for numbers 0-19
        ones = ['', 'eins', 'zwei', 'drei', 'vier', 'fünf', 'sechs', 'sieben', 'acht', 'neun', 'zehn',
                'elf', 'zwölf', 'dreizehn', 'vierzehn', 'fünfzehn', 'sechzehn', 'siebzehn', 'achtzehn', 'neunzehn']
    
        # create a list of the German words for tens
        tens = ['', '', 'zwanzig', 'dreißig', 'vierzig', 'fünfzig', 'sechzig', 'siebzig', 'achtzig', 'neunzig']
    
        # create a list of the German words for larger numbers
        others = ['', 'tausend', 'Million', 'Milliarden', 'Billionen', 'Billiarden']
    
        # handle numbers 0-19
        if number < 20:
            return ones[number]
    
        # handle numbers 20-99
        elif number < 100:
            if number % 10 == 0:
                return tens[number // 10]
            else:
                return ones[number % 10] + 'und' + tens[number // 10]
    
        # handle larger numbers
        else:
            i = 0
            words = ''
            while number > 0:
                if number % 1000 != 0:
                    words = self.spellNumberGerman(number % 1000) + others[i] + ' ' + words
                number //= 1000
                i += 1
            return words.strip()


    def replaceNumbers(self, subtitle):
        
        
        sub = re.sub('(?<=\d),(?=\d)', ' komma ', subtitle )


        # define a regular expression to match numbers
        number_regex = re.compile(r'\d+')

        # find all numbers in the string and replace them with their spelled-out German equivalents
        def replace(match):
            return self.spellNumberGerman(int(match.group()))

        return number_regex.sub(replace, sub)


    # Synthesize a Single Subtilte section using Azure TTS
    def synthesizeSingleSubtitle(self, subtitle, filePath):

        print("Synthesizing Audio with ElevnLab for %s" % filePath)

        api_key = Configuration.elevenlabsAPI
        user = ElevenLabsUser(api_key)
        #print("Characters left: %s" % user.get_character_limit() - user.get_current_character_count() )

        subtitle = self.replaceNumbers(subtitle['content'])
        print(subtitle)

        premadeVoice = user.get_voices_by_name("Bella")[0]
        audioData = premadeVoice.generate_audio_bytes(subtitle, model_id="eleven_multilingual_v1")
        # Save to file using save_to_wav_file method of audio object
        save_audio_bytes(audioData, filePath, outputFormat="wav")

# =============================================================================================================================


    




