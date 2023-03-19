
import json
from datetime import datetime
from flask import (
    Blueprint, flash, g, redirect, render_template, make_response, request, session
)
import requests
from TranslatorApp import Configuration

import pymysql
from flask import Flask, jsonify


class User(object):
    def __init__(self,dbConnection):
        self.dbConnection = dbConnection
        self.name = ''
        self.role = ''

        if Configuration.mode == 'dev':
            self.name = 'Admin'
            self.role = 'administrator'
        else:
            self.checkUserCookie()

    def isAdmin(self):
        return self.role == 'administrator'
        
    def loadRoleFromDB(self):
        #Load UserName From Database
        sql = "select * from %s.`wp_users` where user_login='%s'" % (Configuration.dbDatabase, self.name)
        print(sql)
        #To be finished get the UserID, then load the permissions from wp_usermetadata in wp_capabilities and wp_user_level (Level 10 = administrator)

    #Note: This should be made more secure by validating the Hash Values in the Fields
    def checkUserCookie(self):
        #Function checks if the UserCookie exists and loads permission from DB
        for cookie in request.cookies:
          
            #Check if the cookie matches a substring
            if (cookie[:20] == 'wordpress_logged_in_'):
                #explode value by |
                cookieFields = request.cookies.get(cookie).split('|')
                self.name = cookieFields[0]
                self.role = 'none'

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
    def loadData(self,filter,backlog=True):

        # Only select Items which are in Backlog        
        with self.dbConnection.cursor() as cursor:
            sql = "SELECT * FROM %s.`ka-content`" % Configuration.dbDatabase

            print("Filter is : " + filter)
            where = []
            if (filter == "math16"):
                where.append("course in ('cc-kindergarten-math', 'cc-1st-grade-math', 'cc-2nd-grade-math', 'cc-third-grade-math', 'cc-fourth-grade-math', 'cc-fifth-grade-math', 'cc-sixth-grade-math')")
            
            if (filter == "math713"):
                where.append("course in ('cc-seventh-grade-math', 'cc-eigth-grade-math')")

            if (filter == "computing"):
                where.append("domain = 'computing'")
                where.append("course in ('computer-programming', 'computer-science')")
                
            if (backlog):
                #where.append("backlog='1'")
                where.append("(kind='Video' or kind='Talkthrough')")
                where.append("dubbed='False'")
                where.append("subbed='False'")

            if (len(where)>0):
                sql = sql + " where " + " AND ".join(where)

            print(sql)

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


        return make_response(render_template(
            'videoBacklog.html',
            title='Show Content in the KADeutsch Backlog',
            year=datetime.now().year,
            filter=domainFilter,
            message=self.message,
            user=self.user
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

    #Get
    return v.loadData(filter)

@kabp.route('/data/<id>', methods = ['POST'])
def saveData(id):
    v = KAContent()

    data = {}
    rData = request.get_json()
    
    # Access individual items in the JSON array
    data['id'] = id
    data['translator'] = rData['translator']
    data['translation_date'] = rData['translationDate']
    data['translation_status'] = rData['translationStatus']
    data['translation_comment'] = rData['translationComment']

    return v.saveData(data)

    