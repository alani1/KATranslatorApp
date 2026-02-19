"""YouTube description generator for Khan Academy German dubbed/subbed videos.

Generates title and description text from KA content hierarchy (domain > course > unit > lesson)
and saves it to the database for use when publishing to YouTube.
"""

from TranslatorApp import Configuration
import AIDubbing.Configuration as AIConfiguration
import DBModule

from flask import render_template


# Valid column names for getKAData queries (whitelist to prevent SQL injection)
_VALID_KA_TYPES = {'domain', 'course', 'unit', 'lesson'}


class DescriptionGenerator:
    """Generates YouTube title and description for a Khan Academy video.
    
    Takes a KA content ID (not YouTube ID) and builds a description from
    the content hierarchy (domain, course, unit, lesson) with navigation links.
    """

    def __init__(self, id):
        self.id = id

        self.dbConnection = DBModule.getDBConnection()
        with self.dbConnection.cursor() as cursor:
            sql = "SELECT * FROM `ka-content` WHERE id = %s"
            cursor.execute(sql, (self.id,))
            self.dbData = cursor.fetchone()

    def getKAData(self, type, name):
        """Load a KA content record by type (domain/course/unit/lesson) and name.
        
        Args:
            type: The content kind to query — must be one of 'domain', 'course', 'unit', 'lesson'.
            name: The identifier value to match against the type column.
        
        Returns:
            Dict of the first matching row, or None if not found.
        """
        if type not in _VALID_KA_TYPES:
            print(f"Error: Invalid KA content type '{type}'")
            return None

        sql = f"SELECT * FROM `ka-content` WHERE kind = %s AND `{type}` = %s"
        dbConnection = DBModule.getDBConnection()
        with dbConnection.cursor() as cursor:
            cursor.execute(sql, (type.capitalize(), name))
            for row in cursor.fetchall():
                return row

    def generateYoutubeData(self):
        """Generate YouTube description from KA content hierarchy and save to database.
        
        Builds a description using domain, course, unit, and lesson metadata,
        adds navigation links (previous/next lesson), and renders using the
        YTDescription.txt template. The result is saved to the ka-content table.
        """
        if not self.dbData:
            print(f"Error: No data found for content ID {self.id}")
            return

        values = {}

        values['title'] = self.dbData['translated_title']
        values['kaLink'] = self.dbData['canonical_url']

        domain = self.getKAData("domain", self.dbData['domain'])
        values['domain'] = domain['translated_title'] if domain else ''

        course = self.getKAData("course", self.dbData['course'])
        values['course'] = course['translated_title'] if course else ''
        courseDescription = course['translated_description_html'] if course else ''

        unit = self.getKAData("unit", self.dbData['unit'])
        values['unit'] = unit['translated_title'] if unit else ''
        unitDescription = unit['translated_description_html'] if unit else ''

        lesson = self.getKAData("lesson", self.dbData['lesson'])
        values['lesson'] = lesson['translated_title'] if lesson else ''
        values['description'] = lesson['translated_description_html'] if lesson else ''
                
        # Find previous/next lesson URLs
        dbConnection = DBModule.getDBConnection()
        sql = "SELECT * FROM `ka-content` WHERE lesson = %s"
        with dbConnection.cursor() as cursor:
            cursor.execute(sql, (self.dbData['lesson'],))
            contents = cursor.fetchall()
            print("we have so many " + str(len(contents)))
            for i, content in enumerate(contents):
                if content['id'] == self.dbData['id']:
                    if i > 0:
                        values['previousLesson'] = contents[i - 1]['canonical_url']
                    if i < len(contents) - 1:
                        values['nextLesson'] = contents[i + 1]['canonical_url']
                
        # Translator credit
        if self.dbData['translator'] is not None and len(self.dbData['translator']) > 0:
            values['translator'] = self.dbData['translator'].capitalize() + " von "

        # Lesson description combines course + unit descriptions
        values['lessonDescription'] = courseDescription + unitDescription

        # Channel link from AI Dubbing configuration
        if self.dbData['course'] in AIConfiguration.channelLink:
            values['channelLink'] = AIConfiguration.channelLink[self.dbData['course']]
        else:
            values['channelLink'] = ''

        content = render_template("YTDescription.txt", **values)
        
        # Save the generated description to the DB (parameterized query)
        sql = "UPDATE `ka-content` SET yt_description = %s WHERE youtube_id = %s"
        with dbConnection.cursor() as cursor:
            cursor.execute(sql, (content, self.dbData['youtube_id']))
        dbConnection.commit()
        print("Youtube Description updated in DB")
