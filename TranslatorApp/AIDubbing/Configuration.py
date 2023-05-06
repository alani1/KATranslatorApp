
tts = "azure"
#tts = "elevenlabs"

defaultVoice = "Louisa"
voices = {
    # Nice low pitch voice, very slow so needs 10% speedFactor
    'Louisa' : {
        'voiceName' : "de-DE-LouisaNeural",
        'voiceGender' : "FEMALE",
        'speedFactor' : 1.2 # 1.2 is most natural speed (pleasant)
    },
    # Multilingual Neural voice
    'Jenny' : {
        'voiceName' : "en-US-JennyMultilingualNeural",
        'voiceGender' : "FEMALE",
        'speedFactor' : 1.05  # 1.05 is most natural speed (pleasant)
    },

    'Kasper' : {
        'voiceName' : "de-DE-KasperNeural",
        'voiceGender' : "MALE",
        'speedFactor' : 1.1
    },

    'Amala' : {
        'voiceName' : "de-DE-AmalaNeural",
        'voiceGender' : "FEMALE",
        'speedFactor' : 1.0
    },
}

# Maps Khan Academy Courses to Youtube Playlists on Khan Acadey Deutsch Site
channelLink = {

    "computer-programming" : "https://youtube.com/playlist?list=PLirbHvoUlBTuXp1DRCqINpCwAIyoDgZlp",
    
    "computer-science" :     "https://youtube.com/playlist?list=PLirbHvoUlBTu-dd0lDLqxV-W7KE2Kn9Ge",

    "early-math" :           "https://www.youtube.com/playlist?list=PLirbHvoUlBTtvQF1g0pCAelbj1z-YdT5a",

    "cc-kindergarten-math" : "https://www.youtube.com/playlist?list=PLirbHvoUlBTtoZsuEvOSEdU45_crqojot",   #in German called Mathematik der Vorschule

    "cc-1st-grade-math" :    "https://www.youtube.com/playlist?list=PLirbHvoUlBTv8KXu0o3i0I4Iq3hSuc4KX",   #wrong

    'cc-2nd-grade-math' :    "https://www.youtube.com/playlist?list=PLirbHvoUlBTtA3WcN6a07PGGx_dQLgMod",

    'cc-third-grade-math' :  "https://www.youtube.com/playlist?list=PLirbHvoUlBTvJRODs49zmV5sgutjuULOW",

    'cc-fourth-grade-math' : "https://www.youtube.com/playlist?list=PLirbHvoUlBTsv91OXsB2vKYqP3_K0HFT-",

    'cc-fifth-grade-math' :  "https://www.youtube.com/playlist?list=PLirbHvoUlBTvfbG2vT1SCkU3bASqBKO7A",

    'cc-sixth-grade-math' :  "",
    

    #'basic-geo' : {
    #},

    'geometry' : "https://www.youtube.com/playlist?list=PLirbHvoUlBTthIpU3GWJQS_B-GJxev1j6",

    'cc-seventh-grade-math' : "https://www.youtube.com/playlist?list=PLirbHvoUlBTtE1m_sFJa2UeF81YrvwtHt",


    'cc-eighth-grade-math' :  "",

    'arithmetic' :  "https://youtube.com/playlist?list=PL03E05147AF31CBD7",
    

    'pre-algebra' : "https://www.youtube.com/playlist?list=PLF5752146A89A49EA",


    #'algebra-basics' : {
    #},

    'algebra' : "https://www.youtube.com/playlist?list=PLirbHvoUlBTs1uOBDSCJKaJPtMRVi1JQV",

    #'algebra2' : {
    #},

    #'precalculus' : {
    #},

    #'differential-calculus' : {
    #},

    #'integral-calculus' : {
    #},

    #'multivariable-calculus' : {
    #},

    #'linear-algebra' : {
    #},

    'differential-equations' : "https://youtube.com/playlist?list=PL69002EF42F409C59",

    'trigonometry' : "https://youtube.com/playlist?list=PLEE1721AD37793565",
   
    'statistic' : 'https://youtube.com/playlist?list=PLirbHvoUlBTvKIko_-2mL-hwXshr_os1t'

}