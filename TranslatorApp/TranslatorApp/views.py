"""
Routes and views for the flask application.
"""

from datetime import datetime
from flask import render_template
from TranslatorApp import app, kaContent, subtitle, statistic, glossary, contributions, crowdin_pretranslate

app.register_blueprint(subtitle.bp)
app.register_blueprint(kaContent.kabp)
app.register_blueprint(glossary.bp)
app.register_blueprint(statistic.bp)
app.register_blueprint(contributions.bp)
app.register_blueprint(crowdin_pretranslate.bp)

@app.route('/')
@app.route('/home')
def home():
    """Renders the home page."""
    return render_template(
        'index.html',
        title='Translator Home',
        year=datetime.now().year,
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
