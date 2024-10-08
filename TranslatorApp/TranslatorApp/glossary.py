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

def deeplCreateGlossary(entries):

    url = "https://api-free.deepl.com/v2/glossaries"
    headers = { 'Authorization': 'DeepL-Auth-Key '+ Configuration.deeplAPI }
    data = {
        'name': 'TranslatorApp Glossary',
        'source_lang': "en",
        'target_lang': "de",
        'entries': entries,
        'entries_format': 'tsv'
    }
    result = requests.post(
        url , headers=headers,
        data=data)

    print(result.json())

    ## check the result and do proper error handling
    if result.status_code != 200:
        return "Error: " + result.text
    else:
        return result

def deeplDeleteGlossary(glossaryId):

    url = "https://api-free.deepl.com/v2/glossaries/" + glossaryId
    headers = { 'Authorization': 'DeepL-Auth-Key '+ Configuration.deeplAPI }
    
    result = requests.delete(url, headers=headers)

    ## check the result and do proper error handling
    if result.status_code != 200:
        return "Error: " + result.text
    else:
        return result



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

#This function loads the list of Deeply Glossaries from the API
@bp.route('/data', methods = ['GET'])
def listGlossary():
    glossaryList = ""

    url = "https://api-free.deepl.com/v2/glossaries"
    headers = { 'Authorization': 'DeepL-Auth-Key '+ Configuration.deeplAPI }    
    result = requests.get(url,headers=headers)

    #return the response as json array
    return result.json()

# Create a new Deepl Glossary with the .CSV format created from database
@bp.route('/addGlossary', methods = ['POST'])
def addGlossary():
    message = ""
    glossaryList = ""
    
    db = connectDB()
    user = User(db)

    if request.method == 'POST':
            
        
        cursor = db.cursor()
        cursor.execute("SELECT source, target FROM %s.`ka-glossary` order by id" % Configuration.dbDatabase)
        rows = cursor.fetchall()

        # Generate TSV string
        tsv_string = "\n".join("\t".join(map(str, row.values())).strip() for row in rows)
        #print("TSV data with line numbers:\n", _tsv_string)
        
        dResult = deeplCreateGlossary(tsv_string)
        message = "Data uploaded and glossary created." + dResult
                
    return make_response(render_template('glossary.html',
        title='KA Deutsch - Deepl Glossary Mgmt',
        year=datetime.now().year,
        message=message,
        gloassaryList=glossaryList,
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