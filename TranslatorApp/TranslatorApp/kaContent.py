
import json
from datetime import datetime
from flask import (
    Blueprint, flash, g, redirect, render_template, make_response, request, session
)
import requests
from html import unescape
from TranslatorApp import Configuration

import pymysql
from flask import Flask, jsonify


class User(object):
    def __init__(self,dbConnection):
        self.dbConnection = dbConnection
        self.name = ''
        self.role = ''

        if Configuration.mode == 'dev':
            self.name = Configuration.devUser
            self.role = 'administrator'
            self.user_level = 10
        else:
            self.checkUserCookie()

    def isAdmin(self):
        return self.role == 'administrator'
        
    def loadRoleFromDB(self):
        #Load UserName From Database
        sql = "select * from %s.`wp_users` where user_login='%s'" % (Configuration.dbDatabase, self.name)
        print(sql)
        cursor = self.dbConnection.cursor()
        cursor.execute(sql)
        result = dict(cursor.fetchone())
        #To be finished get the UserID, then load the permissions from wp_usermetadata in wp_capabilities and wp_user_level (Level 10 = administrator)
        ID = result['ID']
        permSQL = "select * from wp_usermeta where user_id='%s' and meta_key='wp_user_level'" % ID
        cursor.execute(permSQL)
        result = dict(cursor.fetchone())
        user_level = int(result['meta_value'])
        if (user_level >= 10):
            self.role = 'administrator'
        else:
            self.role = user_level 

    #Note: This should be made more secure by validating the Hash Values in the Fields
    def checkUserCookie(self):
        #Function checks if the UserCookie exists and loads permission from DB
        for cookie in request.cookies:
            #Check if the cookie matches a substring
            if (cookie[:20] == 'wordpress_logged_in_'):
                #explode value by |
                #Replace escaped pipesymbol
                cookieFields = request.cookies.get(cookie).replace('%7C','|').split('|')
                self.name = cookieFields[0]
                self.role = ''

                self.loadRoleFromDB()


class KAContent(object):

    message = 'Show the Videos in the Backlog'

    def __init__(self):

        self.connectDB()
        self.user = User(self.dbConnection)
    

    def connectDB(self):
        # Connect to the database
        self.dbConnection = pymysql.connect(host=Configuration.dbHost,
                    user=Configuration.dbUser,
                    password=Configuration.dbPassword,
                    db=Configuration.dbDatabase,
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor)


    #Load Data from Content Database
    def loadData(self,user, filter, showAll=False):

        # Only select Items which are in Backlog        
        with self.dbConnection.cursor() as cursor:
            sql = "SELECT * FROM %s.`ka-content`" % Configuration.dbDatabase

            where = []

            if (user != None and user != ''):
                where.append("translator = '%s'" % user)
                if (not showAll):
                    where.append("(translation_status = '' or translation_status = 'Assigned')")
            elif not showAll:
                where.append("(translation_status = '' or translation_status is NULL)")

            if (filter == "math16"):
                where.append("course in ('cc-kindergarten-math', 'cc-1st-grade-math', 'cc-2nd-grade-math', 'cc-third-grade-math', 'cc-fourth-grade-math', 'cc-fifth-grade-math', 'cc-sixth-grade-math')")
            
            if (filter == "math713"):
                where.append("course in ('cc-seventh-grade-math', 'cc-eigth-grade-math')")

            if (filter == "computing"):
                where.append("domain = 'computing'")
                where.append("course in ('computer-programming', 'computer-science')")
            
            #Always filter for Videos which are neither dubbed nor subbed
            if (True):
                #where.append("backlog='1'")
                where.append("(kind='Video' or kind='Talkthrough')")
                where.append("dubbed='False'")
                where.append("subbed='False'")

            if (len(where)>0):
                sql = sql + " where " + " AND ".join(where)

            #print(sql)

            cursor.execute(sql)
            result = cursor.fetchall()
        return jsonify(result)
        
    def saveData(self,data):
        if (len(data)> 0):

            self.connectDB()
            cursor = self.dbConnection.cursor()
            sql = "UPDATE %s.`ka-content` SET " % Configuration.dbDatabase + ', '.join(["{} = '{}'".format(k,v) for k,v in data.items()]) + " WHERE id = '%s'" % data['id']
            #print(sql_statement % ( tuple(data.values()) + (data['id'],)))
            cursor.execute(sql)
            self.dbConnection.commit()
            self.dbConnection.close()

            result = cursor.fetchall()
            return jsonify(result)


        else:
            print("empty data")
        
    def render(self, domainFilter="math16"):

        user = request.args.get('user')
        if ( user != None):
            domainFilter = ''
            userFilter = user
        else:
            domainFilter = 'math16'
            userFilter = ''

        return make_response(render_template(
            'videoBacklog.html',
            title='Show Content in the KADeutsch Backlog',
            year=datetime.now().year,
            filter=domainFilter,
            userFilter=userFilter,
            message=self.message,
            user=self.user,
            baseURL=Configuration.baseURL
        ))                             



#Handle parameters filter="math13,math713, computing" backlog=ignore
kabp = Blueprint('KAContent', __name__, url_prefix='/content')   
@kabp.route('/', methods = ['GET', 'POST'])
def videoBacklog():

    #Create Blueprint Object
    v = KAContent()
    #check if input from filter


    return v.render()

@kabp.route('/data', methods = ['GET'])
def content():

    #Create Blueprint Object
    v = KAContent()

    valid_filters = [ 'math16', 'math713', 'computing'] # List of valid filter parameters
    filter = ""
    iFilter = request.args.get('filter')
    if iFilter in valid_filters:
            filter = iFilter

    user = request.args.get('user')

    showAll = request.args.get('showAll')
    if showAll == None or showAll != '1':
        showAll = False
    else:
        showAll = True

    #Get
    return v.loadData(user, filter, showAll)

@kabp.route('/data/<id>', methods = ['POST'])
def saveData(id):
    v = KAContent()

    if ( not v.user.isAdmin()):
        print("Error: User does not have proper permissions")
        return ""
    
    data = {}
    rData = request.get_json()
    
    # Access individual items in the JSON array
    data['id'] = id
    data['translator'] = rData['translator']
    data['translation_date'] = rData['translationDate']
    data['translation_status'] = rData['translationStatus']
    data['translation_comment'] = rData['translationComment']

    return v.saveData(data)

@kabp.after_request
def set_response_headers(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response   
