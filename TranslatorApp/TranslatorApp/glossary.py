"""Blueprint for DeepL Glossary management — CRUD for glossary entries and DeepL API sync."""

from datetime import datetime
from TranslatorApp import Configuration
from flask import (
    Blueprint, render_template, make_response, request, jsonify
)
import pymysql
import requests
from TranslatorApp.user import User

def deeplGlossaryExists(glossaryId):
    """Check if a glossary exists in DeepL (v3 API)"""
    url = f"https://api-free.deepl.com/v3/glossaries/{glossaryId}"
    headers = {'Authorization': 'DeepL-Auth-Key ' + Configuration.deeplAPI}
    
    try:
        result = requests.get(url, headers=headers, timeout=10)
        return result.status_code == 200
    except requests.RequestException:
        return False


def deeplUpdateGlossary(glossaryId, entries):
    """Update existing glossary entries using DeepL v3 PUT (replaces all entries, preserves ID)"""
    url = f"https://api-free.deepl.com/v3/glossaries/{glossaryId}/dictionaries"
    headers = {
        'Authorization': 'DeepL-Auth-Key ' + Configuration.deeplAPI,
        'Content-Type': 'application/json'
    }
    payload = {
        'source_lang': 'EN',
        'target_lang': 'DE',
        'entries': entries,
        'entries_format': 'tsv'
    }
    
    try:
        result = requests.put(url, headers=headers, json=payload, timeout=30)
        print(f"DeepL v3 Update Response: {result.status_code} - {result.text}")
        
        if result.status_code == 200:
            return {'success': True, 'data': result.json()}
        else:
            return {'success': False, 'error': result.text, 'status_code': result.status_code}
    except requests.RequestException as e:
        return {'success': False, 'error': str(e)}


def deeplCreateGlossary(entries):
    """Create a new glossary using DeepL v3 API"""
    url = "https://api-free.deepl.com/v3/glossaries"
    headers = {
        'Authorization': 'DeepL-Auth-Key ' + Configuration.deeplAPI,
        'Content-Type': 'application/json'
    }
    payload = {
        'name': Configuration.defaultGlossaryName,
        'dictionaries': [{
            'source_lang': 'EN',
            'target_lang': 'DE',
            'entries': entries,
            'entries_format': 'tsv'
        }]
    }
    
    try:
        result = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"DeepL v3 Create Response: {result.status_code} - {result.text}")
        
        if result.status_code in (200, 201):
            data = result.json()
            return {'success': True, 'glossary_id': data.get('glossary_id'), 'data': data}
        else:
            return {'success': False, 'error': result.text, 'status_code': result.status_code}
    except requests.RequestException as e:
        return {'success': False, 'error': str(e)}

def deeplDeleteGlossary(glossaryId):
    """Delete a glossary using DeepL v3 API"""
    url = f"https://api-free.deepl.com/v3/glossaries/{glossaryId}"
    headers = {'Authorization': 'DeepL-Auth-Key ' + Configuration.deeplAPI}
    
    try:
        result = requests.delete(url, headers=headers, timeout=10)
        
        if result.status_code in (200, 204):
            return {'success': True}
        else:
            return {'success': False, 'error': result.text, 'status_code': result.status_code}
    except requests.RequestException as e:
        return {'success': False, 'error': str(e)}



#show statistic
bp = Blueprint('KAGlossary', __name__, url_prefix='/glossary')   
@bp.route('/', methods = ['GET'])

# Main Entry Point for the Glossary Management, show list of Entries from SQL and list of Glossaries from Deepl
def glossary():
    message = ""    
    db = connectDB()
    user = User(db)

    return make_response(render_template('glossary.html',
        title='KA Deutsch - Deepl Glossary Mgmt',
        year=datetime.now().year,
        message=message,
        user=user,
        baseURL=Configuration.baseURL,
    ))


def connectDB():

    # Connect to the database
    dbConnection = pymysql.connect(host=Configuration.dbHost,
                user=Configuration.dbUser,
                password=Configuration.dbPassword,
                db=Configuration.dbDatabase,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor)
    
    return dbConnection

@bp.route('/entries', methods=['GET'])
def listEntries():
    """Return all glossary entries as JSON."""
    db = connectDB()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM `ka-glossary`")
        result = cursor.fetchall()
        cursor.close()
    finally:
        db.close()
    
    return jsonify(result)


@bp.route('/entries/', methods=['POST'])
def createEntry():
    """Create a new glossary entry from POST JSON data. Requires admin."""
    db = connectDB()
    user = User(db)

    if not user.isAdmin():
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    try:
        rData = request.get_json()
        category = rData['category']
        source = rData['source']
        target = rData['target']
        comment = rData['comment']

        cursor = db.cursor()
        sql = "INSERT INTO `ka-glossary` (category, source, target, comment) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (category, source, target, comment))
        result = cursor.fetchall()

        db.commit()
        cursor.close()
    finally:
        db.close()

    return jsonify(result)

@bp.route('/entries/<id>', methods=['POST'])
def saveData(id):
    """Update an existing glossary entry by ID. Requires admin."""
    db = connectDB()
    user = User(db)

    if not user.isAdmin():
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    try:
        rData = request.get_json()
        category = rData['category']
        source = rData['source']
        target = rData['target']
        comment = rData['comment']

        cursor = db.cursor()
        sql = "UPDATE `ka-glossary` SET category = %s, source = %s, target = %s, comment = %s WHERE id = %s"
        cursor.execute(sql, (category, source, target, comment, id))
        result = cursor.fetchall()

        db.commit()
        cursor.close()
    finally:
        db.close()

    return jsonify(result)

@bp.route('/entries/<id>', methods=['DELETE'])
def deleteEntry(id):
    """Delete a glossary entry by ID. Requires admin."""
    db = connectDB()
    user = User(db)

    if not user.isAdmin():
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    try:
        cursor = db.cursor()
        sql = "DELETE FROM `ka-glossary` WHERE id = %s"
        cursor.execute(sql, (id,))
        result = cursor.fetchall()

        db.commit()
        cursor.close()
    finally:
        db.close()

    return jsonify(result)          

#This function loads the list of DeepL Glossaries from the API (v3)
@bp.route('/data', methods = ['GET'])
def listGlossary():
    url = "https://api-free.deepl.com/v3/glossaries"
    headers = {'Authorization': 'DeepL-Auth-Key ' + Configuration.deeplAPI}
    
    try:
        result = requests.get(url, headers=headers, timeout=10)
        data = result.json()
        
        # Transform v3 response to match expected format for UI
        # v3 returns dictionaries array instead of entry_count directly
        glossaries = data.get('glossaries', [])
        for g in glossaries:
            # Get entry_count from first dictionary if available
            dictionaries = g.get('dictionaries', [])
            if dictionaries:
                g['entry_count'] = dictionaries[0].get('entry_count', 0)
            else:
                g['entry_count'] = 0
        
        return jsonify({'glossaries': glossaries})
    except requests.RequestException as e:
        return jsonify({'error': str(e), 'glossaries': []})

# Update existing DeepL Glossary or create new one if not exists (v3 API)
@bp.route('/addGlossary', methods = ['POST'])
def addGlossary():
    message = ""
    newGlossaryWarning = False
    newGlossaryId = None
    
    db = connectDB()
    user = User(db)

    if request.method == 'POST':
        cursor = db.cursor()
        cursor.execute("SELECT source, target FROM `ka-glossary` ORDER BY id")
        rows = cursor.fetchall()

        # Generate TSV string
        tsv_string = "\n".join("\t".join(map(str, row.values())).strip() for row in rows)
        
        # Check if default glossary exists
        glossaryId = Configuration.defaultGlossaryId
        
        if deeplGlossaryExists(glossaryId):
            # Update existing glossary (preserves ID)
            result = deeplUpdateGlossary(glossaryId, tsv_string)
            if result.get('success'):
                message = f"Glossary updated successfully! (ID: {glossaryId})"
            else:
                message = f"Error updating glossary: {result.get('error', 'Unknown error')}"
        else:
            # Glossary doesn't exist - create a new one
            result = deeplCreateGlossary(tsv_string)
            if result.get('success'):
                newGlossaryId = result.get('glossary_id')
                newGlossaryWarning = True
                message = f"New glossary created with ID: {newGlossaryId}"
            else:
                message = f"Error creating glossary: {result.get('error', 'Unknown error')}"
                
    return make_response(render_template('glossary.html',
        title='KA Deutsch - Deepl Glossary Mgmt',
        year=datetime.now().year,
        message=message,
        newGlossaryWarning=newGlossaryWarning,
        newGlossaryId=newGlossaryId,
        user=user,
        baseURL=Configuration.baseURL,
    ))

@bp.route('/deleteGlossary/<id>', methods = ['DELETE'])
def deleteGlossary(id):

    db = connectDB()
    user = User(db)

    if not user.isAdmin():
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    result = deeplDeleteGlossary(id)

    return jsonify(result)  

@bp.after_request
def set_response_headers(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response  