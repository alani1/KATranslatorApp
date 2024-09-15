
import json
from datetime import datetime
from flask import (
    Blueprint, flash, g, redirect, render_template, make_response, request, session
)
import requests
from html import unescape
from TranslatorApp import Configuration
from TranslatorApp.user import User
from TranslatorApp.YoutubeDescriptionGenerator import DescriptionGenerator


import pymysql
from flask import Flask, jsonify



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

    def focusCourseCondition(self, course):
        if not course in Configuration.focusCourses and course != 'all':
            return ''

        if (course == 'all'):
            cCourses = []
            for course in Configuration.focusCourses:
                cCourses.append(self.focusCourseCondition(course))

            return ', '.join(cCourses)
        else:
            courses = Configuration.focusCourses[course]['courses']
            cCourses = []
            for c in courses:
                cCourses.append("'%s'" % c)

            return ', '.join(cCourses)

    # Load all users with permission contributore (1 or higher)
    def getUsers(self):

        with self.dbConnection.cursor() as cursor:
            sql = "SELECT user_nicename FROM %s.wp_users, %s.wp_usermeta WHERE wp_users.id = wp_usermeta.user_id AND wp_usermeta.meta_key='wp_user_level' AND wp_usermeta.meta_value > 0 ORDER BY user_login" % (Configuration.dbDatabase,Configuration.dbDatabase)
            cursor.execute(sql)
            result = cursor.fetchall()
            return result

    #Check if Video is already assigned to User
    def ifAssigned(self, id):
        
        with self.dbConnection.cursor() as cursor:
            sql = "SELECT * FROM %s.`ka-content` where id='%s' AND translator IS NULL" % (Configuration.dbDatabase, id)

            cursor.execute(sql)
            result = cursor.fetchall()
            
            if len(result)>0:
                return False

        return True

    #Load Data from Content Database
    def loadData(self,user, filter, showAll=False):

        noDuplicates = False
        # Only select Items which are in Backlog        
        with self.dbConnection.cursor() as cursor:
            sql = "SELECT * FROM %s.`ka-content`" % Configuration.dbDatabase

            where = []

            #When user specified show only this users Backlog
            if (user != None and user != ''):
                where.append("translator = '%s'" % user)

                if (not showAll):
                    where.append("(translation_status = '' or translation_status = 'Assigned')")
            
            #Limit to not Translated Videos unless showAll is specified or "approval-backlog"
            elif (not showAll) and filter != "approval" and filter != "assigned" and filter != "publish":
                where.append("(translation_status = '' or translation_status is NULL)")
            
            #build filterCondtion for focus courses
            filterCondition = self.focusCourseCondition(filter)
            if (filter == "approval"):
                noDuplicates = True
                where.append("(translation_status = 'Translated')")

            if (filter == "assigned"):
                noDuplicates = True
                where.append("(translation_status = 'Assigned')")

            # Include all Published Courses
            if (filter == "publish"):
                noDuplicates = True
                
                where.append("( `ka-content`.dubbed = 'True' or `ka-content`.subbed = 'True' ) AND `ka-content`.listed_anywhere = 'False'")
                where.append("course in (%s)" % self.focusCourseCondition("all"))

            if (filter in Configuration.focusCourses):
                where.append("course in (%s)" % filterCondition)

            # For Computing we add domain = 'computing' and filter for the courses, not sure this is required
            if (filter == "computing"):
                where.append("domain = 'computing'")
                where.append("course in (%s)" % filterCondition)
            
            #Always filter for Videos which are neither dubbed nor subbed
            if (True):
                #where.append("backlog='1'")
                where.append("(kind='Video' or kind='Talkthrough')")

            if ( not showAll and filter != "publish"):
                where.append("dubbed='False'")
                where.append("subbed='False'")

            if (len(where)>0):
                sql = sql + " where " + " AND ".join(where)

            #Add Group By to avoid duplicates
            if (noDuplicates):
                sql = sql + " GROUP BY id"

            print(sql)

            cursor.execute(sql)
            result = cursor.fetchall()
        return jsonify(result)


    

    def saveData(self,data):
        if (len(data)> 0):

            self.connectDB()
            cursor = self.dbConnection.cursor()
            sql = "UPDATE %s.`ka-content` SET " % Configuration.dbDatabase + ', '.join(["{} = '{}'".format(k,v) for k,v in data.items()]) + " WHERE id = '%s'" % data['id']

            cursor.execute(sql)
            self.dbConnection.commit()
            self.dbConnection.close()

            # Generate the Youtube Description
            ytData = DescriptionGenerator(data['id'])
            ytData.generateYoutubeData()


            result = cursor.fetchall()
            return jsonify(result)


        else:
            print("empty data")
        
    def render(self, domainFilter="math713"):

        user = request.args.get('user')
        if ( user != None):
            domainFilter = ''
            userFilter = user
        else:
            domainFilter = 'math713'
            userFilter = ''

        domains = {}
        for course in Configuration.focusCourses:
            if Configuration.focusCourses[course]['visible']:
                
                # Only show those courses a user is allowed to see
                # check if adminOnly Key is set and if the user is an admin
                if not Configuration.focusCourses[course].get('adminOnly', False):
                    domains[course] = Configuration.focusCourses[course]['name']
                else:
                    if self.user != None and self.user.role == 'administrator':
                            domains[course] = Configuration.focusCourses[course]['name']

        return make_response(render_template(
            'videoBacklog.html',
            title='Show Content in the KADeutsch Backlog',
            year=datetime.now().year,
            filter=domainFilter,
            domains=domains,
            userFilter=userFilter,
            message=self.message,
            user=self.user,
            users=self.getUsers(),
            baseURL=Configuration.baseURL,
        ))                             



#Handle parameters filter="math13,math713, computing" backlog=ignore
#Generate HTML with List and Edit Dialog
kabp = Blueprint('KAContent', __name__, url_prefix='/content')   
@kabp.route('/', methods = ['GET', 'POST'])
def videoBacklog():

    #Create Blueprint Object
    v = KAContent()
    #check if input from filter


    return v.render()

#genrate json with all filtered content
@kabp.route('/data', methods = ['GET'])
def content():

    #Create Blueprint Object
    v = KAContent()

    # List of valid filter parameters
    valid_filters = [ 'approval', 'assigned', 'publish' ] 
    for course in Configuration.focusCourses:
        if Configuration.focusCourses[course]['visible']:
            valid_filters.append(course)

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

@kabp.route('/assign/<id>', methods = ['POST'])
def assignToUser(id):
    v = KAContent()

    if ( not v.user.isContributor()):
        print("Assignment-Error: User does not have proper permissions")
        return jsonify("")
    
    data = {}
    data['id'] = id
    data['translator'] = v.user.name
    data['translation_date'] = datetime.today().strftime("%Y-%m-%d")
    data['translation_status'] = "Assigned"

    #TODO: Check if the Content Element is not assigned alreay (Status must be empty!)
    if (v.ifAssigned(id)):
        print("Error: The Video is already assigned to user")
        return jsonify("The Video is already assigned to user")
    else:
        return v.saveData(data)

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
