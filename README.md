# TranslatorApp

A Flask-based web application for managing Khan Academy translations with DeepL integration and Crowdin pre-translation capabilities.

## Features

- **Glossary Management**: Create and manage DeepL glossaries for consistent translations
- **Crowdin Pre-Translation**: Automatically download files from Crowdin, translate untranslated strings via DeepL, and upload back
- **Translation Statistics**: Track translation progress and contributor statistics
- **Video Backlog**: Manage video translation backlog

## Setup

### Prerequisites

- Python 3.x
- MySQL database
- DeepL API key (free tier supported)
- Crowdin account and API key (for pre-translation feature)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/alani1/KATranslatorApp.git
cd KATranslatorApp/TranslatorApp
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the application:
```bash
cd TranslatorApp
cp Configuration.example.py Configuration.py
```

4. Edit `Configuration.py` with your settings:
   - Database credentials
   - DeepL API key
   - Base URL
   - Focus courses

5. Run the application:
```bash
python runserver.py
```

## Using the Crowdin Pre-Translation Feature

The Crowdin Pre-Translation feature allows you to automatically translate untranslated strings in Crowdin files using DeepL.

### How it works:

1. **Download**: The tool downloads a file from your Crowdin project using the File ID
2. **Identify**: It identifies all untranslated strings in the file
3. **Translate**: It translates those strings using DeepL API (with optional glossary support)
4. **Upload**: It uploads the translations back to Crowdin

### Usage:

1. Navigate to the "Pre-Translate" page in the application
2. Enter the following parameters:
   - **Crowdin API Key**: Your Crowdin Personal Access Token
   - **Project ID**: Your Crowdin project ID (found in project settings)
   - **File ID**: The ID of the file you want to translate (found in file properties)
   - **DeepL API Key**: Your DeepL API key (free tier supported)
   - **Glossary ID** (optional): DeepL glossary ID for consistent terminology

3. Check "Remember credentials in browser" to save the parameters in localStorage
4. Click "Start Pre-Translation"

### Finding IDs:

- **Crowdin Project ID**: Found in your Crowdin project settings or in the URL
- **Crowdin File ID**: Available through the Crowdin API or file properties
- **DeepL Glossary ID**: Create and manage glossaries in the "Glossary" section

### Security Notes:

- Credentials are stored in browser localStorage only (not on the server)
- Configuration.py is gitignored to prevent accidental credential commits
- Only administrators can access the pre-translation feature

## Contributing

Contributions are welcome! Please ensure your code follows the existing style and structure.

## License

[Add license information here]
