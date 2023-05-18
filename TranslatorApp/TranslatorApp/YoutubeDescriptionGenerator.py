
from TranslatorApp import Configuration
import AIDubbing.Configuration as AIConfiguration
import DBModule

from flask import render_template
from jinja2 import Environment, FileSystemLoader


# ======================================== Class to Generate Youtube Title and Description ================================================================

class DescriptionGenerator:
    """Class to generation the Description for a Youtube Video"""

    # Takes KA Id and not YT Id as input!
    def __init__(self, id):
        self.id = id

        self.dbConnection = DBModule.getDBConnection()
        with self.dbConnection.cursor() as cursor:
            sql = "SELECT * FROM %s.`ka-content`" % Configuration.dbDatabase + " where id='%s'" % self.id
            cursor.execute(sql)
            self.dbData = cursor.fetchone()

    def getKAData(self, type, name):

        #Load Data from lesson record, check the Caps for type in Kind it needs to start with capital letter
        sql = "SELECT * FROM %s.`ka-content`" % Configuration.dbDatabase + " where kind = '%s' and %s = '%s'" % (type.capitalize(), type, name)
        dbConnection = DBModule.getDBConnection()
        with dbConnection.cursor() as cursor:
            cursor.execute(sql)
            for row in cursor.fetchall():
                return row

    # Generates the Youtube Description for the Video and save it to the DataBase
    def generateYoutubeData(self):

        values = {}

        values['title'] = self.dbData['translated_title']
        values['kaLink'] = self.dbData['canonical_url']

        domain = self.getKAData("domain", self.dbData['domain'])
        values['domain'] = domain['translated_title']

        course = self.getKAData("course", self.dbData['course'])
        values['course'] = course['translated_title']
        courseDescription = course['translated_description_html']

        unit = self.getKAData("unit", self.dbData['unit'])
        values['unit'] = unit['translated_title']
        unitDescription = unit['translated_description_html']

        lesson = self.getKAData("lesson", self.dbData['lesson'])
        values['lesson'] = lesson['translated_title']
        values['description'] = lesson['translated_description_html']
                
        #nextLesson
        #previousLesson

        dbConnection = DBModule.getDBConnection()
        #select all rows with same lesson
        sql = "SELECT * FROM %s.`ka-content`" % Configuration.dbDatabase + " where lesson = '%s'" % self.dbData['lesson']
        with dbConnection.cursor() as cursor2:
            cursor2.execute(sql)
            contents = cursor2.fetchall()
            i = 0
            for content in contents:
                if(content['id'] == self.dbData['id']):
                    #print("found the same id and it is row %s" % i)
                    values['previousLesson'] = contents[i-1]['canonical_url']
                    values['nextLesson'] = contents[i+1]['canonical_url']
                i+=1
                
        #translator
        if (self.dbData['translator'] != None and len(self.dbData['translator']) > 0):
            values['translator'] = self.dbData['translator'].capitalize() + " von "

        # generate lessonDescription, takes the course description and adds the unit description
        values['lessonDescription'] = courseDescription + unitDescription

        #channelLink
        #Check if the course exists in AIDubbing Configuration
        if (self.dbData['course'] in AIConfiguration.channelLink):
            values['channelLink'] =AIConfiguration.channelLink[self.dbData['course']]
        else:
            values['channelLink'] = ''

        content = render_template("YTDescription.txt",**values)
        print(content)
        #print(values)

        # Save the generated Description to the DB

        sql = "UPDATE %s.`ka-content`" % Configuration.dbDatabase + " SET yt_description = '%s' where youtube_id = '%s'" % (content, self.dbData['youtube_id'] )
        with dbConnection.cursor() as cursor:
            cursor.execute(sql)
        dbConnection.commit()
        print("Youtube Description updated in DB")
