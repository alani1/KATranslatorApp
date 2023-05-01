
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

    def __init__(self, YTid, kind="Video", voice=""):
        super().__init__(YTid, kind, voice)
# ======================================== Audio Synthesizing and processing ==================================================

    # Synthesize a Single Subtilte section using Azure TTS
    def synthesizeSingleSubtitle(self, subtitle, filePath):

        print("Synthesizing Audio with ElevnLab for %s" % filePath)

        api_key = "5017388514bdf3f5b64adccc51fa6a06"
        user = ElevenLabsUser(api_key)
        print("Characters left: %s" % user.get_current_character_count() )

        print(subtitle['content'])

        premadeVoice = user.get_voices_by_name("Bella")[0]
        audioData = premadeVoice.generate_audio_bytes(subtitle['content'], model_id="eleven_multilingual_v1")
        # Save to file using save_to_wav_file method of audio object
        save_audio_bytes(audioData, filePath, outputFormat="wav")

# =============================================================================================================================


    




