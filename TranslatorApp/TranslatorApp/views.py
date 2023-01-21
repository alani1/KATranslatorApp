"""
Routes and views for the flask application.
"""

from datetime import datetime
from flask import render_template
from TranslatorApp import app, subtitle

@app.route('/')
@app.route('/home')
def home():
    """Renders the home page."""
    return render_template(
        'index.html',
        title='Translator Home',
        year=datetime.now().year,
    )

@app.route('/subtitlesOLD', methods = ['GET', 'POST'])
def subtitlesOLD():
    """Renders the subtitle translation page."""

    st = subtitle.hello();

    return render_template(
        'subtitle.html',
        title='Subtitle',
        year=datetime.now().year,
        message='Subtitle translation page.',
        subtitle=st
    )

@app.route('/about')
def about():
    """Renders the about page."""
    return render_template(
        'about.html',
        title='About KA Deutsch',
        year=datetime.now().year,
        message='Your application description page.'
    )
