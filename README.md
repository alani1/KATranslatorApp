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

The Crowdin Pre-Translation feature uses a three-step workflow that gives you full control over which strings to translate and prevents unnecessary DeepL API usage.

### How it works:

**Step 1: Fetch Strings from Crowdin**
- Downloads all strings from a Crowdin file using the File ID
- Shows existing German translations
- Strings with existing German translations are **automatically unchecked**

**Step 2: Translate with DeepL**
- Select which strings you want to translate (uncheck any you don't want to translate)
- Click "Translate Selected Strings" to send only the selected strings to DeepL
- Review and edit the DeepL translations before uploading

**Step 3: Upload to Crowdin**
- Upload the final reviewed translations back to Crowdin
- Only checked translations are uploaded

### Usage:

1. Navigate to the "Pre-Translate" page in the application
2. **Step 1: Fetch Strings**
   - Enter your **Crowdin API Key** (Personal Access Token)
   - Enter your **Project ID** (found in project settings)
   - Enter the **File ID** you want to translate (found in file properties)
   - Click "Step 1: Fetch Strings from Crowdin"
   - Review the list of strings (those with existing German translations are unchecked)

3. **Step 2: Translate**
   - Enter your **DeepL API Key** (free tier supported)
   - Optionally enter a **Glossary ID** for consistent terminology
   - Select the strings you want to translate (check/uncheck as needed)
   - Click "Step 2: Translate Selected Strings with DeepL"
   - Review and edit the translations as needed

4. **Step 3: Upload**
   - Make any final edits to the translations
   - Uncheck any translations you don't want to upload
   - Click "Step 3: Upload to Crowdin"

5. Check "Remember credentials in browser" to save your settings in localStorage (browser only, not on server)

### Finding IDs:

- **Crowdin Project ID**: Found in your Crowdin project settings or in the URL
- **Crowdin File ID**: Available through the Crowdin API or file properties
- **DeepL Glossary ID**: Create and manage glossaries in the "Glossary" section

### Security Notes:

- Credentials are stored in browser localStorage only (not on the server)
- Configuration.py is gitignored to prevent accidental credential commits
- Only administrators can access the pre-translation feature

## Database Migrations

The app uses a lightweight SQL migration runner (`migrate.py`) to track and apply schema changes. Migrations live in the `TranslatorApp/migrations/` folder and are applied in filename order.

### Running Migrations

```bash
cd TranslatorApp
python migrate.py
```

This will:
- Create a `schema_migrations` table (if it doesn't exist) to track applied migrations
- Apply any `.sql` files in `migrations/` that haven't been run yet
- Skip already-applied migrations safely (idempotent)

### Applied Migrations

| Migration | Description |
|-----------|-------------|
| `0001_widen_thumbnail_url.sql` | Widens `thumbnail_url` column on `ka-content` table from VARCHAR(140) to VARCHAR(500). Required because TSV exports from the Translation Portal contain thumbnail URLs that exceed the old 140-character limit, causing a `DataError` in `TranslationPortalUpdate.py`. |

### Adding a New Migration

Create a new `.sql` file in `TranslatorApp/migrations/` with a sequential prefix, e.g.:

```
migrations/0002_your_description.sql
```

The file should contain plain SQL statements separated by semicolons. Comment lines (`--`) are ignored. Run `python migrate.py` to apply it.

## Contributing

Contributions are welcome! Please ensure your code follows the existing style and structure.

## License

[Add license information here]
