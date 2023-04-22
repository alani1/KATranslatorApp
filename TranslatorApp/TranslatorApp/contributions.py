from wsgiref.handlers import read_environ
from flask import (
    Blueprint, flash, g, redirect, render_template, make_response, request, session
)
from TranslatorApp import Configuration
import pymysql


def connectDB():
    # Connect to the database
    return pymysql.connect(host=Configuration.dbHost,
                user=Configuration.dbUser,
                password=Configuration.dbPassword,
                db=Configuration.dbDatabase,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor)

def contributions(name):



    # Connect to the database
    dbCon = connectDB()
    cursor = dbCon.cursor()


    sql = "SELECT * FROM `ka-content` WHERE translator='%s' AND translation_status IN ('Translated') ORDER BY translation_date desc" % name
 
    cursor.execute(sql)
    translated = cursor.fetchall()

    sql = "SELECT * FROM `ka-content` WHERE translator='%s' AND translation_status IN ('Approved') ORDER BY translation_date desc" % name
    cursor.execute(sql)
    reviewed = cursor.fetchall()

    sql = "SELECT * FROM `ka-content` WHERE translator='%s' AND translation_status IN ('Native Dubbed', 'AI Dubbed', 'Approved') AND listed='True' ORDER BY translation_date desc" % name
    print(sql)
    cursor.execute(sql)
    published = cursor.fetchall()


    return render_template(
        'contributions.html',
        userName=name,
        translatedCount=len(translated),
        translatedSubtitles=translated,
        reviewedCount=len(reviewed),
        reviewedSubtitles=reviewed,
        publishedCount=len(published),
        publishedSubtitles=published
        )

bp = Blueprint('Contribution', __name__, url_prefix='/contribution')
@bp.route('/<name>', methods = ['GET'])
def contribution(name):


    return contributions(name)
