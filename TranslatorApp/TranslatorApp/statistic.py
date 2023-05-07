from datetime import datetime
from TranslatorApp import Configuration
from flask import (
    Blueprint, flash, g, redirect, render_template, make_response, request, session
)
import pymysql

def focusCourseCondition(course):

    if not course in Configuration.focusCourses:
        return ''

    courses = Configuration.focusCourses[course]

    cCourses = []
    for c in courses:
        cCourses.append("'%s'" % c)

    return ', '.join(cCourses)


def generateCourseStatistic(course):

    courseData = dict()
    courseData["name"] = course
    courseData["topicChampion"] = Configuration.topicChampion[course]

    dbConnection = pymysql.connect(host=Configuration.dbHost,
                user=Configuration.dbUser,
                password=Configuration.dbPassword,
                db=Configuration.dbDatabase,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor)

    #Get Video Statistics
    sql = "SELECT distinct id, COUNT(*) AS total, SUM(dubbed = 'True') AS dubbed, SUM(subbed = 'True' AND dubbed = 'False') AS subbed,  SUM(translation_status = 'Approved' AND (subbed = 'False' AND dubbed = 'False') ) AS sub_translated FROM `ka-content` WHERE (kind='Video' or kind='Talkthrough') and `course` IN (%s)" % focusCourseCondition(course)
    
    with dbConnection.cursor() as cursor:
        elements = ""
        cursor.execute(sql)
        result = cursor.fetchone()
        result['todo'] = result['total'] - result['dubbed'] - result['subbed'] - result['sub_translated']
        courseData["videos"] = result

    #Get Word Statistics
    sql = "SELECT SUM(word_count) AS word_count, SUM(approved_count) AS approved_count, SUM(translated_count) AS translated_count FROM `ka-content` WHERE `course` IN (%s)" % focusCourseCondition(course) 
    with dbConnection.cursor() as cursor:
        cursor.execute(sql)
        result = cursor.fetchone()
        
        courseData["words"] = result
    
    #Get Revisions


    return courseData

#Generate Statistic per Translator    
def getTranslatorStatistic():
    sql = "SELECT translator, COUNT(DISTINCT id) AS total, COUNT(DISTINCT CASE WHEN (translation_status='Approved' OR translation_status='Translated') AND translation_date >= DATE_ADD(NOW(), INTERVAL -30 DAY) THEN id END) AS DAY30, COUNT(DISTINCT CASE WHEN translation_status='Approved' OR translation_status='Translated' THEN id END) AS Translated, COUNT(DISTINCT CASE WHEN translation_status='Assigned' THEN id END) AS Assigned, COUNT(DISTINCT CASE WHEN translation_status='AI Dubbed' THEN id END) AS AIDubbed, COUNT(DISTINCT CASE WHEN translation_status='Native Dubbed' THEN id END) AS Dubbed, MAX(translation_date) AS LastActivity FROM `ka-content` WHERE translator NOT IN ('None', 'null', '') GROUP BY translator ORDER BY DAY30 DESC;"

    dbConnection = pymysql.connect(host=Configuration.dbHost,
                user=Configuration.dbUser,
                password=Configuration.dbPassword,
                db=Configuration.dbDatabase,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor)

    data = dict()
    with dbConnection.cursor() as cursor:
        cursor.execute(sql)
        result = cursor.fetchall()

        return result





    return data

#show statistic
bp = Blueprint('KAStatistic', __name__, url_prefix='/statistic')   
@bp.route('/', methods = ['GET'])
def statistic():

    message = ""
    courses = dict()
    translators = []


    for course in Configuration.focusCourses:
        
        courseStat = generateCourseStatistic(course)
        courses[course] = courseStat

    #Translator Statistic
    translators = getTranslatorStatistic()
    total=0
    translated=0
    day30=0
    assigned=0
    dubbed=0
    aidubbed=0
    
    for translator in translators:
        total= total + translator['total']
        translated= translated + translator['Translated']
        day30= day30 + translator['DAY30']
        assigned= assigned + translator['Assigned']
        dubbed= dubbed + translator['Dubbed']
        aidubbed= aidubbed + translator['AIDubbed']

    translatorsTotal = {'total': total, 'translated': translated, 'DAY30': day30, 'Assigned': assigned, 'Dubbed': dubbed, 'AIDubbed': aidubbed}
    

    return make_response(render_template(
        'statistic.html',
        title='KA Deutsch - Translation Statistics',
        year=datetime.now().year,
        message=message,
        courses=courses,
        translators=translators,
        translatorsTotal=translatorsTotal,
        baseURL=Configuration.baseURL
)) 