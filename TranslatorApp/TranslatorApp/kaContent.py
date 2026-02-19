"""Blueprint for Khan Academy content backlog management — video assignment, status tracking, and filtering."""

import json
from datetime import datetime
from flask import (
    Blueprint, render_template, make_response, request, jsonify
)
import requests
from html import unescape
from TranslatorApp import Configuration
from TranslatorApp.user import User
from TranslatorApp.YoutubeDescriptionGenerator import DescriptionGenerator

import pymysql



class KAContent(object):
    """Manages Khan Academy content backlog — video listing, assignment, and status updates."""

    message = 'Show the Videos in the Backlog'

    def __init__(self):
        self.connectDB()
        self.user = User(self.dbConnection)
    

    def connectDB(self):
        """Create and store a new database connection."""
        self.dbConnection = pymysql.connect(host=Configuration.dbHost,
                    user=Configuration.dbUser,
                    password=Configuration.dbPassword,
                    db=Configuration.dbDatabase,
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor)

    def focusCourseCondition(self, course):
        """Build a SQL IN-clause value list for the given course group.
        
        Args:
            course: A key from Configuration.focusCourses, or 'all' for all courses.
        
        Returns:
            Comma-separated quoted course names for use in SQL IN clauses.
        """
        if course not in Configuration.focusCourses and course != 'all':
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
        """Load all users with contributor permissions (level > 0)."""
        with self.dbConnection.cursor() as cursor:
            sql = ("SELECT user_nicename FROM wp_users, wp_usermeta "
                   "WHERE wp_users.id = wp_usermeta.user_id "
                   "AND wp_usermeta.meta_key = 'wp_user_level' "
                   "AND wp_usermeta.meta_value > 0 ORDER BY user_login")
            cursor.execute(sql)
            result = cursor.fetchall()
            return result

    def ifAssigned(self, id):
        """Check if a video is already assigned to a user.
        
        Returns:
            True if the video IS assigned (translator is not NULL), False otherwise.
        """
        with self.dbConnection.cursor() as cursor:
            sql = "SELECT * FROM `ka-content` WHERE id = %s AND translator IS NULL"
            cursor.execute(sql, (id,))
            result = cursor.fetchall()
            
            if len(result) > 0:
                return False

        return True

    def loadData(self, user, filter, showAll=False):
        """Load content items from database with filtering.
        
        Args:
            user: Optional translator username to filter by.
            filter: Course group key or special filter ('approval', 'assigned', 'publish').
            showAll: If True, include all statuses regardless of filter.
        
        Returns:
            JSON response with matching content items.
        """
        noDuplicates = False
        params = []

        with self.dbConnection.cursor() as cursor:
            sql = "SELECT * FROM `ka-content`"

            where = []

            # When user specified, show only this user's backlog
            if user is not None and user != '':
                where.append("translator = %s")
                params.append(user)

                if not showAll:
                    where.append("(translation_status = '' OR translation_status = 'Assigned')")
            
            # Limit to untranslated videos unless showAll or special filter
            elif (not showAll) and filter != "approval" and filter != "assigned" and filter != "publish":
                where.append("(translation_status = '' OR translation_status IS NULL)")
            
            # Build filter condition for focus courses
            filterCondition = self.focusCourseCondition(filter)
            if filter == "approval":
                noDuplicates = True
                where.append("(translation_status = 'Translated')")

            if filter == "assigned":
                noDuplicates = True
                where.append("(translation_status = 'Assigned')")

            if filter == "publish":
                noDuplicates = True
                
                where.append("( `ka-content`.dubbed = 'True' or `ka-content`.subbed = 'True' ) AND `ka-content`.listed_anywhere = 'False'")
                where.append("course in (%s)" % self.focusCourseCondition("all"))

            if filter in Configuration.focusCourses:
                where.append("course in (%s)" % filterCondition)

            if filter == "computing":
                where.append("domain = 'computing'")
                where.append("course in (%s)" % filterCondition)
            
            # Always filter for video content types
            where.append("(kind='Video' OR kind='Talkthrough')")

            if not showAll and filter != "publish":
                where.append("dubbed='False'")
                where.append("subbed='False'")

            if len(where) > 0:
                sql = sql + " WHERE " + " AND ".join(where)

            # Add GROUP BY to avoid duplicates
            if noDuplicates:
                sql = sql + " GROUP BY id"

            print(sql)

            cursor.execute(sql, params)
            result = cursor.fetchall()
        return jsonify(result)


    

    def saveData(self, data):
        """Save updated content data to the database.
        
        Updates specific allowed fields for a content item, then triggers
        YouTube description generation.
        
        Args:
            data: Dict with 'id' and fields to update (translator, translation_date,
                  translation_status, translation_comment).
        
        Returns:
            JSON response confirming the update.
        """
        if len(data) == 0:
            print("empty data")
            return jsonify({'error': 'No data provided'}), 400

        self.connectDB()
        cursor = self.dbConnection.cursor()
        try:
            # Parameterized UPDATE with explicit allowed columns
            allowed_fields = ['translator', 'translation_date', 'translation_status', 'translation_comment']
            set_clauses = []
            values = []
            for field in allowed_fields:
                if field in data:
                    set_clauses.append(f"`{field}` = %s")
                    values.append(data[field])
            
            if not set_clauses:
                return jsonify({'error': 'No valid fields to update'}), 400

            values.append(data['id'])
            sql = "UPDATE `ka-content` SET " + ', '.join(set_clauses) + " WHERE id = %s"
            cursor.execute(sql, tuple(values))
            self.dbConnection.commit()
            cursor.close()
        finally:
            self.dbConnection.close()

        # Generate the YouTube Description
        ytData = DescriptionGenerator(data['id'])
        ytData.generateYoutubeData()

        return jsonify({'success': True})
        
    def render(self, domainFilter="math16"):

        user = request.args.get('user')
        if ( user != None):
            domainFilter = ''
            userFilter = user
        else:
            domainFilter = 'math16'
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

    if not v.user.isContributor():
        print("Assignment-Error: User does not have proper permissions")
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    data = {}
    data['id'] = id
    data['translator'] = v.user.name
    data['translation_date'] = datetime.today().strftime("%Y-%m-%d")
    data['translation_status'] = "Assigned"

    #TODO: Check if the Content Element is not assigned already (Status must be empty!)
    if v.ifAssigned(id):
        print("Error: The Video is already assigned to user")
        return jsonify("The Video is already assigned to user")
    else:
        return v.saveData(data)

@kabp.route('/data/<id>', methods = ['POST'])
def saveData(id):
    v = KAContent()

    if not v.user.isAdmin():
        return jsonify({'error': 'Insufficient permissions'}), 403
    
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
