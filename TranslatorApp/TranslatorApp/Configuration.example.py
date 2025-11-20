## Configuration file for TranslatorApp
## Copy this file to Configuration.py and fill in your actual values
## DO NOT commit Configuration.py to version control

# Database Configuration
dbHost = 'localhost'
dbUser = 'your_db_user'
dbPassword = 'your_db_password'
dbDatabase = 'translator_db'

# DeepL API Configuration
# Get your API key from: https://www.deepl.com/pro-api
deeplAPI = 'your-deepl-api-key-here'

# Base URL for the application
# Example: 'http://localhost:5000' for local development
# or 'https://yourdomain.com/TranslatorApp' for production
baseURL = 'http://localhost:5000'

# Focus Courses Configuration
# Define the courses you want to track in statistics
focusCourses = {
    'math': {
        'name': 'Mathematics',
        'visible': True,
        'topicChampion': 'User1',
        'courses': ['math-basics', 'algebra']
    },
    # Add more courses as needed
}
