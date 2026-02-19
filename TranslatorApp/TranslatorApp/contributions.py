"""Contributor profile page showing translated, reviewed, and published subtitles."""

from flask import Blueprint, render_template, request
from TranslatorApp import Configuration
import pymysql


def connectDB():
    """Create and return a new database connection."""
    return pymysql.connect(host=Configuration.dbHost,
                user=Configuration.dbUser,
                password=Configuration.dbPassword,
                db=Configuration.dbDatabase,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor)


def contributions(name):
    """Render the contributions page for a given translator.
    
    Queries the database for all subtitles translated, reviewed, and published
    by the named contributor, and renders the contributions template.
    
    Args:
        name: The translator's username (from URL path parameter).
    
    Returns:
        Rendered HTML template with contribution statistics.
    """
    dbCon = connectDB()
    try:
        cursor = dbCon.cursor()

        # Parameterized queries to prevent SQL injection
        sql = "SELECT * FROM `ka-content` WHERE translator = %s AND translation_status IN ('Translated') GROUP BY id ORDER BY translation_date DESC"
        cursor.execute(sql, (name,))
        translated = cursor.fetchall()

        sql = "SELECT * FROM `ka-content` WHERE translator = %s AND translation_status IN ('Approved') GROUP BY id ORDER BY translation_date DESC"
        cursor.execute(sql, (name,))
        reviewed = cursor.fetchall()

        sql = "SELECT * FROM `ka-content` WHERE translator = %s AND translation_status IN ('Native Dubbed', 'AI Dubbed', 'Approved') AND listed = 'True' GROUP BY id ORDER BY translation_date DESC"
        cursor.execute(sql, (name,))
        published = cursor.fetchall()

        cursor.close()
    finally:
        dbCon.close()

    totalLength = 0
    totalViewCount = 0
    for v in published:
        totalLength = totalLength + int(v['duration'])
        if v['yt_views'] is not None:
            totalViewCount = totalViewCount + int(v['yt_views'])

    return render_template(
        'contributions.html',
        userName=name,
        baseURL=Configuration.baseURL,
        translatedCount=len(translated),
        translatedSubtitles=translated,
        reviewedCount=len(reviewed),
        reviewedSubtitles=reviewed,
        publishedCount=len(published),
        publishedSubtitles=published,
        totalLength=totalLength,
        totalViewCount=totalViewCount
    )


bp = Blueprint('Contribution', __name__, url_prefix='/contribution')

@bp.route('/<name>', methods=['GET'])
def contribution(name):
    """Route handler for /contribution/<name>."""
    return contributions(name)
