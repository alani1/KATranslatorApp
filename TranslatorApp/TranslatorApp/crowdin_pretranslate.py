## Module / Blueprint to manage Crowdin Pre-Translation with DeepL

from datetime import datetime
from TranslatorApp import Configuration
from flask import (
    Blueprint, flash, g, redirect, render_template, make_response, request, session, jsonify
)
import pymysql
import requests
from TranslatorApp.user import User

def crowdinDownloadFile(projectId, fileId, apiKey):
    """
    Download a file from Crowdin project
    
    Args:
        projectId: Crowdin project ID
        fileId: Crowdin file ID to download
        apiKey: Crowdin API key
    
    Returns:
        dict: File content and metadata
    """
    try:
        # First, build the file for export
        url = f"https://api.crowdin.com/api/v2/projects/{projectId}/files/{fileId}/download"
        headers = {
            'Authorization': f'Bearer {apiKey}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            return {
                'success': False,
                'error': f"Failed to download file: {response.text}"
            }
        
        download_data = response.json()
        
        # Download the actual file from the URL provided
        file_url = download_data.get('data', {}).get('url')
        if not file_url:
            return {
                'success': False,
                'error': "No download URL in response"
            }
        
        file_response = requests.get(file_url)
        
        if file_response.status_code != 200:
            return {
                'success': False,
                'error': f"Failed to download file content: {file_response.text}"
            }
        
        return {
            'success': True,
            'content': file_response.text,
            'url': file_url
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Exception during download: {str(e)}"
        }

def crowdinUploadTranslation(projectId, fileId, apiKey, content, targetLang='de'):
    """
    Upload translations back to Crowdin
    
    Args:
        projectId: Crowdin project ID
        fileId: Crowdin file ID to upload to
        apiKey: Crowdin API key
        content: Translated content to upload
        targetLang: Target language code (default: 'de' for German)
    
    Returns:
        dict: Upload result
    """
    try:
        # First, upload the file to storage
        storage_url = f"https://api.crowdin.com/api/v2/storages"
        headers = {
            'Authorization': f'Bearer {apiKey}',
            'Crowdin-API-FileName': 'translation.json'
        }
        
        files = {
            'file': ('translation.json', content, 'application/json')
        }
        
        storage_response = requests.post(storage_url, headers=headers, files=files)
        
        if storage_response.status_code not in [200, 201]:
            return {
                'success': False,
                'error': f"Failed to upload to storage: {storage_response.text}"
            }
        
        storage_data = storage_response.json()
        storage_id = storage_data.get('data', {}).get('id')
        
        if not storage_id:
            return {
                'success': False,
                'error': "No storage ID in response"
            }
        
        # Now upload the translations
        upload_url = f"https://api.crowdin.com/api/v2/projects/{projectId}/translations/{targetLang}"
        headers = {
            'Authorization': f'Bearer {apiKey}',
            'Content-Type': 'application/json'
        }
        
        upload_data = {
            'storageId': storage_id,
            'fileId': fileId
        }
        
        upload_response = requests.post(upload_url, headers=headers, json=upload_data)
        
        if upload_response.status_code not in [200, 201]:
            return {
                'success': False,
                'error': f"Failed to upload translations: {upload_response.text}"
            }
        
        return {
            'success': True,
            'data': upload_response.json()
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Exception during upload: {str(e)}"
        }

def deeplTranslateStrings(strings, apiKey, glossaryId=None, sourceLang='en', targetLang='de', formality='less'):
    """
    Translate strings using DeepL API
    
    Args:
        strings: List of strings to translate
        apiKey: DeepL API key
        glossaryId: Optional DeepL glossary ID
        sourceLang: Source language code (default: 'en')
        targetLang: Target language code (default: 'de')
        formality: Formality level - 'less' for informal (default), 'more' for formal
    
    Returns:
        dict: Translated strings
    """
    try:
        url = "https://api-free.deepl.com/v2/translate"
        headers = {
            'Authorization': f'DeepL-Auth-Key {apiKey}'
        }
        
        translations = []
        
        # Translate in batches to avoid rate limits
        batch_size = 50
        for i in range(0, len(strings), batch_size):
            batch = strings[i:i+batch_size]
            
            data = {
                'text': batch,
                'source_lang': sourceLang.upper(),
                'target_lang': targetLang.upper(),
                'formality': formality
            }
            
            if glossaryId:
                data['glossary_id'] = glossaryId
            
            response = requests.post(url, headers=headers, data=data)
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f"DeepL API error: {response.text}"
                }
            
            result = response.json()
            batch_translations = [t['text'] for t in result.get('translations', [])]
            translations.extend(batch_translations)
        
        return {
            'success': True,
            'translations': translations
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Exception during translation: {str(e)}"
        }

def getTranslationsForReview(projectId, fileId, crowdinApiKey, deeplApiKey, glossaryId=None):
    """
    Download file, translate, and return translations for user review
    Does NOT upload to Crowdin yet
    
    Args:
        projectId: Crowdin project ID
        fileId: Crowdin file ID
        crowdinApiKey: Crowdin API key
        deeplApiKey: DeepL API key
        glossaryId: Optional DeepL glossary ID
    
    Returns:
        dict: Translation pairs for review
    """
    result = {
        'success': False,
        'translations': [],
        'errors': []
    }
    
    # Step 1: Download file from Crowdin
    download_result = crowdinDownloadFile(projectId, fileId, crowdinApiKey)
    if not download_result['success']:
        result['errors'].append(download_result['error'])
        return result
    
    # Parse the content (assuming JSON format)
    try:
        import json
        file_content = json.loads(download_result['content'])
    except Exception as e:
        result['errors'].append(f"Failed to parse file content: {str(e)}")
        return result
    
    # Step 2: Identify untranslated strings
    untranslated_strings = []
    string_keys = []
    
    # Handle different file formats
    if isinstance(file_content, dict):
        for key, value in file_content.items():
            if isinstance(value, str):
                # Simple key-value format
                if not value or value == key:
                    untranslated_strings.append(key)
                    string_keys.append(key)
            elif isinstance(value, dict) and 'translation' in value:
                # Structured format with translation field
                if not value.get('translation'):
                    untranslated_strings.append(value.get('source', key))
                    string_keys.append(key)
    
    if not untranslated_strings:
        result['success'] = True
        result['message'] = "No untranslated strings found"
        return result
    
    # Step 3: Translate via DeepL with informal formality
    translation_result = deeplTranslateStrings(
        untranslated_strings,
        deeplApiKey,
        glossaryId=glossaryId,
        formality='less'  # Use informal voice
    )
    
    if not translation_result['success']:
        result['errors'].append(translation_result['error'])
        return result
    
    # Step 4: Prepare translation pairs for review
    translations = translation_result['translations']
    translation_pairs = []
    
    for i, key in enumerate(string_keys):
        if i < len(translations):
            translation_pairs.append({
                'key': key,
                'source': untranslated_strings[i],
                'translation': translations[i]
            })
    
    result['success'] = True
    result['translations'] = translation_pairs
    
    return result

def uploadReviewedTranslations(projectId, fileId, crowdinApiKey, translationPairs):
    """
    Upload reviewed and approved translations to Crowdin
    
    Args:
        projectId: Crowdin project ID
        fileId: Crowdin file ID
        crowdinApiKey: Crowdin API key
        translationPairs: List of translation pairs with key, source, translation
    
    Returns:
        dict: Upload result
    """
    result = {
        'success': False,
        'uploaded': 0,
        'errors': []
    }
    
    try:
        import json
        
        # Download the original file to get the structure
        download_result = crowdinDownloadFile(projectId, fileId, crowdinApiKey)
        if not download_result['success']:
            result['errors'].append(download_result['error'])
            return result
        
        file_content = json.loads(download_result['content'])
        
        # Update file content with reviewed translations
        for pair in translationPairs:
            key = pair['key']
            translation = pair['translation']
            
            if key in file_content:
                if isinstance(file_content[key], str):
                    file_content[key] = translation
                elif isinstance(file_content[key], dict):
                    file_content[key]['translation'] = translation
        
        # Upload to Crowdin
        updated_content = json.dumps(file_content, ensure_ascii=False, indent=2)
        upload_result = crowdinUploadTranslation(
            projectId,
            fileId,
            crowdinApiKey,
            updated_content
        )
        
        if not upload_result['success']:
            result['errors'].append(upload_result['error'])
            return result
        
        result['uploaded'] = len(translationPairs)
        result['success'] = True
        
        return result
        
    except Exception as e:
        result['errors'].append(f"Exception during upload: {str(e)}")
        return result

def processPreTranslation(projectId, fileId, crowdinApiKey, deeplApiKey, glossaryId=None):
    """
    Main function to process pre-translation:
    1. Download file from Crowdin
    2. Identify untranslated strings
    3. Translate via DeepL
    4. Upload back to Crowdin
    
    Args:
        projectId: Crowdin project ID
        fileId: Crowdin file ID
        crowdinApiKey: Crowdin API key
        deeplApiKey: DeepL API key
        glossaryId: Optional DeepL glossary ID
    
    Returns:
        dict: Process result with statistics
    """
    result = {
        'success': False,
        'downloaded': 0,
        'untranslated': 0,
        'translated': 0,
        'uploaded': 0,
        'errors': []
    }
    
    # Step 1: Download file from Crowdin
    download_result = crowdinDownloadFile(projectId, fileId, crowdinApiKey)
    if not download_result['success']:
        result['errors'].append(download_result['error'])
        return result
    
    result['downloaded'] = 1
    
    # Parse the content (assuming JSON format)
    try:
        import json
        file_content = json.loads(download_result['content'])
    except Exception as e:
        result['errors'].append(f"Failed to parse file content: {str(e)}")
        return result
    
    # Step 2: Identify untranslated strings
    # This depends on the file format, but typically we look for empty translations
    untranslated_strings = []
    string_keys = []
    
    # Handle different file formats
    if isinstance(file_content, dict):
        for key, value in file_content.items():
            if isinstance(value, str):
                # Simple key-value format
                if not value or value == key:
                    untranslated_strings.append(key)
                    string_keys.append(key)
            elif isinstance(value, dict) and 'translation' in value:
                # Structured format with translation field
                if not value.get('translation'):
                    untranslated_strings.append(value.get('source', key))
                    string_keys.append(key)
    
    result['untranslated'] = len(untranslated_strings)
    
    if not untranslated_strings:
        result['success'] = True
        result['message'] = "No untranslated strings found"
        return result
    
    # Step 3: Translate via DeepL
    translation_result = deeplTranslateStrings(
        untranslated_strings,
        deeplApiKey,
        glossaryId=glossaryId
    )
    
    if not translation_result['success']:
        result['errors'].append(translation_result['error'])
        return result
    
    result['translated'] = len(translation_result['translations'])
    
    # Step 4: Update the file content with translations
    translations = translation_result['translations']
    for i, key in enumerate(string_keys):
        if i < len(translations):
            if isinstance(file_content[key], str):
                file_content[key] = translations[i]
            elif isinstance(file_content[key], dict):
                file_content[key]['translation'] = translations[i]
    
    # Step 5: Upload back to Crowdin
    updated_content = json.dumps(file_content, ensure_ascii=False, indent=2)
    upload_result = crowdinUploadTranslation(
        projectId,
        fileId,
        crowdinApiKey,
        updated_content
    )
    
    if not upload_result['success']:
        result['errors'].append(upload_result['error'])
        return result
    
    result['uploaded'] = 1
    result['success'] = True
    
    return result

def connectDB():
    """Connect to the database"""
    dbConnection = pymysql.connect(
        host=Configuration.dbHost,
        user=Configuration.dbUser,
        password=Configuration.dbPassword,
        db=Configuration.dbDatabase,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    return dbConnection

# Blueprint setup
bp = Blueprint('CrowdinPreTranslate', __name__, url_prefix='/pretranslate')

@bp.route('/', methods=['GET'])
def pretranslate():
    """Main entry point for the Pre-Translation page"""
    message = ""
    db = connectDB()
    user = User(db)
    
    return make_response(render_template(
        'pretranslate.html',
        title='KA Deutsch - Crowdin Pre-Translation',
        year=datetime.now().year,
        message=message,
        user=user,
        baseURL=Configuration.baseURL,
    ))

@bp.route('/translate', methods=['POST'])
def translate():
    """Get translations for review (Step 1)"""
    db = connectDB()
    user = User(db)
    
    if not user.isAdmin():
        return jsonify({
            'success': False,
            'error': 'User does not have proper permissions'
        }), 403
    
    try:
        data = request.get_json()
        
        projectId = data.get('projectId')
        fileId = data.get('fileId')
        crowdinApiKey = data.get('crowdinApiKey')
        deeplApiKey = data.get('deeplApiKey')
        glossaryId = data.get('glossaryId')
        
        # Validate required parameters
        if not all([projectId, fileId, crowdinApiKey, deeplApiKey]):
            return jsonify({
                'success': False,
                'error': 'Missing required parameters'
            }), 400
        
        # Get translations for review
        result = getTranslationsForReview(
            projectId,
            fileId,
            crowdinApiKey,
            deeplApiKey,
            glossaryId if glossaryId else None
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Exception: {str(e)}'
        }), 500

@bp.route('/upload', methods=['POST'])
def upload():
    """Upload reviewed translations to Crowdin (Step 2)"""
    db = connectDB()
    user = User(db)
    
    if not user.isAdmin():
        return jsonify({
            'success': False,
            'error': 'User does not have proper permissions'
        }), 403
    
    try:
        data = request.get_json()
        
        projectId = data.get('projectId')
        fileId = data.get('fileId')
        crowdinApiKey = data.get('crowdinApiKey')
        translationPairs = data.get('translations', [])
        
        # Validate required parameters
        if not all([projectId, fileId, crowdinApiKey]):
            return jsonify({
                'success': False,
                'error': 'Missing required parameters'
            }), 400
        
        if not translationPairs:
            return jsonify({
                'success': False,
                'error': 'No translations to upload'
            }), 400
        
        # Upload reviewed translations
        result = uploadReviewedTranslations(
            projectId,
            fileId,
            crowdinApiKey,
            translationPairs
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Exception: {str(e)}'
        }), 500

@bp.route('/process', methods=['POST'])
def process():
    """Process pre-translation request (legacy endpoint - now redirects to two-step flow)"""
    db = connectDB()
    user = User(db)
    
    if not user.isAdmin():
        return jsonify({
            'success': False,
            'error': 'User does not have proper permissions'
        }), 403
    
    try:
        data = request.get_json()
        
        projectId = data.get('projectId')
        fileId = data.get('fileId')
        crowdinApiKey = data.get('crowdinApiKey')
        deeplApiKey = data.get('deeplApiKey')
        glossaryId = data.get('glossaryId')
        
        # Validate required parameters
        if not all([projectId, fileId, crowdinApiKey, deeplApiKey]):
            return jsonify({
                'success': False,
                'error': 'Missing required parameters'
            }), 400
        
        # Process the pre-translation
        result = processPreTranslation(
            projectId,
            fileId,
            crowdinApiKey,
            deeplApiKey,
            glossaryId if glossaryId else None
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Exception: {str(e)}'
        }), 500

@bp.after_request
def set_response_headers(response):
    """Set cache control headers"""
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
