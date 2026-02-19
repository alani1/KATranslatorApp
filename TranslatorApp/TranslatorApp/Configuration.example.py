"""Configuration template for TranslatorApp.

Copy this file to Configuration.py and fill in your actual values.
DO NOT commit Configuration.py to version control — it is gitignored.
"""

# ── DeepL API ──────────────────────────────────────────────────
# Get your API key from: https://www.deepl.com/pro-api
deeplAPI = 'your-deepl-api-key-here'
defaultGlossaryId = 'your-deepl-glossary-id'            # DeepL v3 Glossary ID (update if recreated)
defaultGlossaryName = 'TranslatorApp Glossary'

# ── Amara API ──────────────────────────────────────────────────
# Get your API key from: https://amara.org/profiles/account
amaraADMIN = 'your-amara-admin-api-key'                  # Amara Admin API key
amaraAPI = 'your-amara-user-api-key'                      # Amara regular user API key

# ── Google / YouTube API ───────────────────────────────────────
googleAPI = 'your-google-api-key'

# ── ElevenLabs API ─────────────────────────────────────────────
elevenlabsAPI = 'your-elevenlabs-api-key'

# ── Discord Webhook ────────────────────────────────────────────
discordWebhookURL = 'https://discordapp.com/api/webhooks/your-webhook-url'

# ── Azure Speech API ───────────────────────────────────────────
azure_speech_key = 'your-azure-speech-key'
azure_speech_region = 'eastus'                            # e.g. 'eastus', 'westeurope'

# ── TTS Engine Selection ───────────────────────────────────────
# Options: 'azure' or 'elevenlabs'
tts = 'elevenlabs'

# ── Database Settings ──────────────────────────────────────────
dbHost = 'localhost'
dbUser = 'your_db_user'
dbPassword = 'your_db_password'
dbDatabase = 'kadeutsch'

# ── Application Settings ──────────────────────────────────────
baseURL = ''                                              # e.g. '' for dev, 'https://yourdomain.com' for prod
mode = 'dev'                                              # 'dev' = skip cookie auth, use devUser
devUser = 'your_username'                                 # Used when mode='dev'

# ── Flask Secret Key ──────────────────────────────────────────
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
secret_key = 'generate-a-random-secret-key'

# ── Focus Courses ─────────────────────────────────────────────
# Define the Khan Academy courses to track. Each entry needs:
#   name         : Display name
#   courses      : List of KA course slugs
#   visible      : Show in UI navigation
#   adminOnly    : (optional) Only show to admin users
#   topicChampion: Responsible person's name, or 'vacant'
focusCourses = {
    'math16': {
        'name': 'Mathe 1-6',
        'courses': ['cc-kindergarten-math', 'cc-1st-grade-math'],
        'visible': True,
        'topicChampion': 'Your Name',
    },
    # Add more course groups as needed
}
