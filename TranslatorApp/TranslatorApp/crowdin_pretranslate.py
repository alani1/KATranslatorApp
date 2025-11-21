## Module / Blueprint to manage Crowdin Pre-Translation with DeepL

from datetime import datetime
from TranslatorApp import Configuration
from flask import (
    Blueprint, flash, g, redirect, render_template, make_response, request, session, jsonify
)
import pymysql
import requests
import json
from TranslatorApp.user import User

def crowdinGetStrings(projectId, fileId, apiKey, limit=500):
    """
    Fetch strings from a Crowdin file using the string-level API
    (accessible to Translator and Proofreader roles)
    
    Args:
        projectId: Crowdin project ID
        fileId: Crowdin file ID
        apiKey: Crowdin API key
        limit: Maximum number of strings to fetch per request (default: 500)
    
    Returns:
        dict: Contains 'success', 'strings' (list of string objects), 
              and 'virtual_content' (JSON mapping identifier->text)
    """
    try:
        url = f"https://api.crowdin.com/api/v2/projects/{projectId}/strings"
        headers = {
            'Authorization': f'Bearer {apiKey}',
            'Content-Type': 'application/json'
        }
        
        all_strings = []
        offset = 0
        
        # Paginate through all strings for this file
        while True:
            params = {
                'fileId': fileId,
                'limit': limit,
                'offset': offset
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f"Failed to fetch strings: {response.text}"
                }
            
            result = response.json()
            data_items = result.get('data', [])
            
            if not data_items:
                break
            
            # Extract string information
            for item in data_items:
                string_data = item.get('data', {})
                string_id = string_data.get('id')
                identifier = string_data.get('identifier') or f"string_{string_id}"
                text = string_data.get('text', '')
                
                all_strings.append({
                    'id': string_id,
                    'identifier': identifier,
                    'text': text
                })
            
            # Check if there are more pages
            pagination = result.get('pagination', {})
            if offset + limit >= pagination.get('total', 0):
                break
            
            offset += limit
        
        # Build virtual file content (identifier -> text mapping)
        virtual_content = {}
        for string_obj in all_strings:
            virtual_content[string_obj['identifier']] = string_obj['text']
        
        virtual_content_json = json.dumps(virtual_content, ensure_ascii=False, indent=2)
        
        return {
            'success': True,
            'strings': all_strings,
            'virtual_content': virtual_content_json
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Exception during string fetch: {str(e)}"
        }

def crowdinUploadStringTranslations(projectId, apiKey, stringTranslations, targetLang='de'):
    """
    Upload translations to Crowdin using string-level API
    (accessible to Translator and Proofreader roles)
    
    Args:
        projectId: Crowdin project ID
        apiKey: Crowdin API key
        stringTranslations: List of dicts with 'stringId' and 'text' keys
        targetLang: Target language code (default: 'de' for German)
    
    Returns:
        dict: Upload result with success status and count
    """
    try:
        url = f"https://api.crowdin.com/api/v2/projects/{projectId}/translations"
        headers = {
            'Authorization': f'Bearer {apiKey}',
            'Content-Type': 'application/json'
        }
        
        uploaded_count = 0
        errors = []
        
        # Upload translations for each string
        for item in stringTranslations:
            string_id = item.get('stringId')
            translation_text = item.get('text')
            
            if not string_id or translation_text is None:
                errors.append(f"Missing stringId or text in translation item: {item}")
                continue
            
            payload = {
                'stringId': string_id,
                'text': translation_text,
                'languageId': targetLang
            }
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code not in [200, 201]:
                errors.append(f"Failed to upload translation for string {string_id}: {response.text}")
            else:
                uploaded_count += 1
        
        if errors and uploaded_count == 0:
            return {
                'success': False,
                'error': f"Failed to upload translations: {'; '.join(errors[:3])}"
            }
        
        return {
            'success': True,
            'uploaded': uploaded_count,
            'errors': errors if errors else []
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Exception during upload: {str(e)}"
        }

def getDeeplUsage(apiKey):
    """
    Get DeepL API usage statistics
    
    Args:
        apiKey: DeepL API key
    
    Returns:
        dict: Usage information including character_count, character_limit, and remaining
    
    Note:
        Currently uses the Free API endpoint. For Pro API keys, the endpoint
        should be 'https://api.deepl.com/v2/usage' (without '-free'). 
        Both endpoints work with their respective API keys.
    """
    try:
        # Note: This uses the free API endpoint. Pro keys work on both endpoints,
        # but for consistency with deeplTranslateStrings, we use the free endpoint.
        url = "https://api-free.deepl.com/v2/usage"
        headers = {
            'Authorization': f'DeepL-Auth-Key {apiKey}'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            return {
                'success': False,
                'error': f"DeepL API error: {response.text}"
            }
        
        result = response.json()
        character_count = result.get('character_count', 0)
        character_limit = result.get('character_limit', 0)
        
        return {
            'success': True,
            'character_count': character_count,
            'character_limit': character_limit,
            'character_remaining': character_limit - character_count
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Exception during usage fetch: {str(e)}"
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
    Fetch strings, translate, and return translations for user review
    Does NOT upload to Crowdin yet
    
    Args:
        projectId: Crowdin project ID
        fileId: Crowdin file ID
        crowdinApiKey: Crowdin API key
        deeplApiKey: DeepL API key
        glossaryId: Optional DeepL glossary ID
    
    Returns:
        dict: Translation pairs for review (includes stringId)
    """
    result = {
        'success': False,
        'translations': [],
        'errors': []
    }
    
    # Step 1: Fetch strings from Crowdin using string-level API
    strings_result = crowdinGetStrings(projectId, fileId, crowdinApiKey)
    if not strings_result['success']:
        result['errors'].append(strings_result['error'])
        return result
    
    all_strings = strings_result['strings']
    
    # Step 2: Identify untranslated strings (for now, treat all as needing translation)
    untranslated_strings = []
    string_mapping = []  # To track stringId, identifier, and source text
    
    for string_obj in all_strings:
        untranslated_strings.append(string_obj['text'])
        string_mapping.append({
            'stringId': string_obj['id'],
            'identifier': string_obj['identifier'],
            'source': string_obj['text']
        })
    
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
    
    # Step 4: Prepare translation pairs for review (including stringId)
    translations = translation_result['translations']
    translation_pairs = []
    
    for i, mapping in enumerate(string_mapping):
        if i < len(translations):
            translation_pairs.append({
                'key': mapping['identifier'],
                'source': mapping['source'],
                'translation': translations[i],
                'stringId': mapping['stringId']  # Include stringId for upload
            })
    
    result['success'] = True
    result['translations'] = translation_pairs
    
    return result

def uploadReviewedTranslations(projectId, fileId, crowdinApiKey, translationPairs, targetLang='de'):
    """
    Upload reviewed and approved translations to Crowdin using string-level API
    
    Args:
        projectId: Crowdin project ID
        fileId: Crowdin file ID (kept for API compatibility but not used)
        crowdinApiKey: Crowdin API key
        translationPairs: List of translation pairs with key, source, translation, and stringId
        targetLang: Target language code (default: 'de' for German)
    
    Returns:
        dict: Upload result
    """
    result = {
        'success': False,
        'uploaded': 0,
        'errors': []
    }
    
    try:
        # Convert translation pairs to string translations format
        string_translations = []
        
        for pair in translationPairs:
            string_id = pair.get('stringId')
            translation = pair.get('translation')
            
            if not string_id:
                result['errors'].append(f"Missing stringId in translation pair: {pair.get('key', 'unknown')}")
                continue
            
            if translation is None or translation == '':
                result['errors'].append(f"Empty translation for key: {pair.get('key', 'unknown')}")
                continue
            
            string_translations.append({
                'stringId': string_id,
                'text': translation
            })
        
        if not string_translations:
            result['errors'].append("No valid translations to upload")
            return result
        
        # Upload to Crowdin using string-level API
        upload_result = crowdinUploadStringTranslations(
            projectId,
            crowdinApiKey,
            string_translations,
            targetLang
        )
        
        if not upload_result['success']:
            result['errors'].append(upload_result['error'])
            return result
        
        result['uploaded'] = upload_result['uploaded']
        result['success'] = True
        
        if upload_result.get('errors'):
            result['errors'].extend(upload_result['errors'])
        
        return result
        
    except Exception as e:
        result['errors'].append(f"Exception during upload: {str(e)}")
        return result

def processPreTranslation(projectId, fileId, crowdinApiKey, deeplApiKey, glossaryId=None, targetLang='de'):
    """
    Main function to process pre-translation:
    1. Fetch strings from Crowdin
    2. Identify untranslated strings
    3. Translate via DeepL
    4. Upload back to Crowdin using string-level API
    
    Args:
        projectId: Crowdin project ID
        fileId: Crowdin file ID
        crowdinApiKey: Crowdin API key
        deeplApiKey: DeepL API key
        glossaryId: Optional DeepL glossary ID
        targetLang: Target language code (default: 'de' for German)
    
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
    
    # Step 1: Fetch strings from Crowdin using string-level API
    strings_result = crowdinGetStrings(projectId, fileId, crowdinApiKey)
    if not strings_result['success']:
        result['errors'].append(strings_result['error'])
        return result
    
    result['downloaded'] = 1
    all_strings = strings_result['strings']
    
    # Step 2: Identify untranslated strings (treat all as needing translation)
    untranslated_strings = []
    string_translations = []  # To track stringId and text for upload
    
    for string_obj in all_strings:
        untranslated_strings.append(string_obj['text'])
        string_translations.append({
            'stringId': string_obj['id'],
            'source': string_obj['text']
        })
    
    result['untranslated'] = len(untranslated_strings)
    
    if not untranslated_strings:
        result['success'] = True
        result['message'] = "No untranslated strings found"
        return result
    
    # Step 3: Translate via DeepL (with configurable targetLang)
    translation_result = deeplTranslateStrings(
        untranslated_strings,
        deeplApiKey,
        glossaryId=glossaryId,
        targetLang=targetLang
    )
    
    if not translation_result['success']:
        result['errors'].append(translation_result['error'])
        return result
    
    result['translated'] = len(translation_result['translations'])
    
    # Step 4: Prepare translations for upload
    translations = translation_result['translations']
    upload_items = []
    
    for i, item in enumerate(string_translations):
        if i < len(translations):
            upload_items.append({
                'stringId': item['stringId'],
                'text': translations[i]
            })
    
    # Step 5: Upload to Crowdin using string-level API
    upload_result = crowdinUploadStringTranslations(
        projectId,
        crowdinApiKey,
        upload_items,
        targetLang
    )
    
    if not upload_result['success']:
        result['errors'].append(upload_result['error'])
        return result
    
    result['uploaded'] = upload_result['uploaded']
    result['success'] = True
    
    if upload_result.get('errors'):
        result['errors'].extend(upload_result['errors'])
    
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
        targetLang = data.get('targetLang', 'de')  # Default to German
        
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
            translationPairs,
            targetLang
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Exception: {str(e)}'
        }), 500

@bp.route('/process', methods=['POST'])
def process():
    """Process pre-translation request (legacy endpoint - one-step flow)"""
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
        targetLang = data.get('targetLang', 'de')  # Default to German
        
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
            glossaryId if glossaryId else None,
            targetLang
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Exception: {str(e)}'
        }), 500

@bp.route('/deepl-usage', methods=['POST'])
def deepl_usage():
    """Get DeepL API usage statistics"""
    db = connectDB()
    user = User(db)
    
    if not user.isAdmin():
        return jsonify({
            'success': False,
            'error': 'User does not have proper permissions'
        }), 403
    
    try:
        data = request.get_json()
        deeplApiKey = data.get('deeplApiKey')
        
        if not deeplApiKey:
            return jsonify({
                'success': False,
                'error': 'DeepL API key is required'
            }), 400
        
        # Get usage information
        result = getDeeplUsage(deeplApiKey)
        
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
