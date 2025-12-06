## Module / Blueprint to manage DeepL Glossaries

from datetime import datetime
from pickletools import read_stringnl_noescape_pair
from TranslatorApp import Configuration
from flask import (
    Blueprint, flash, g, redirect, render_template, make_response, request, session, jsonify
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

@bp.route('/entries', methods = ['GET'])
def listEntries():
    entries = []
    #db = pymysql.connect(host=Configuration.dbHost, user=Configuration.dbUser, password=Configuration.dbPassword, db=Configuration.dbDatabase)
    db = connectDB()
    cursor = db.cursor()
    cursor.execute("SELECT * from %s.`ka-glossary`" % Configuration.dbDatabase)
    result = cursor.fetchall()
    
    return jsonify(result)


#this function creates glossary entries to the database
@bp.route('/entries/', methods = ['POST'])
def createEntry():
    db = connectDB()
    user = User(db)

    if ( not user.isAdmin()):
        print("Error: User does not have proper permissions")
        return ""
    
    data = {}
    rData = request.get_json()
    
    # Access individual items in the JSON array
    data['category'] = rData['category']
    data['source'] = rData['source']
    data['target'] = rData['target']
    data['comment'] = rData['comment']

    cursor = db.cursor()
    sql = "INSERT INTO %s.`ka-glossary` (%s) VALUES ('%s')" % (Configuration.dbDatabase, ', '.join(data.keys()), "', '".join(data.values()))
    print(sql)
    cursor.execute(sql)
    result = cursor.fetchall()
            
    db.commit()
    db.close()

    return jsonify(result)

#this function saves glossary entries to the database
@bp.route('/entries/<id>', methods = ['POST'])
def saveData(id):

    db = connectDB()
    user = User(db)

    if ( not user.isAdmin()):
        print("Error: User does not have proper permissions")
        return ""
    
    data = {}
    rData = request.get_json()
    
    # Access individual items in the JSON array
    data['id'] = id
    data['category'] = rData['category']
    data['source'] = rData['source']
    data['target'] = rData['target']
    data['comment'] = rData['comment']

    cursor = db.cursor()
    sql = "UPDATE %s.`ka-glossary` SET " % Configuration.dbDatabase + ', '.join(["{} = '{}'".format(k,v) for k,v in data.items()]) + " WHERE id = '%s'" % data['id']

    cursor.execute(sql)
    result = cursor.fetchall()
            
    db.commit()
    db.close()

    return jsonify(result)

@bp.route('/entries/<id>', methods = ['DELETE'])
def deleteEntry(id):

    db = connectDB()
    user = User(db)

    if ( not user.isAdmin()):
        print("Error: User does not have proper permissions")
        return ""
    
    cursor = db.cursor()
    sql = "DELETE FROM %s.`ka-glossary` WHERE id = '%s'" % (Configuration.dbDatabase, id)
    cursor.execute(sql)
    result = cursor.fetchall()
            
    db.commit()
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
        cursor.execute("SELECT source, target FROM %s.`ka-glossary` order by id" % Configuration.dbDatabase)
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

    if ( not user.isAdmin()):
        print("Error: User does not have proper permissions")
        return ""
    
    result = deeplDeleteGlossary(id)

    return jsonify(result)  

@bp.after_request
def set_response_headers(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response  