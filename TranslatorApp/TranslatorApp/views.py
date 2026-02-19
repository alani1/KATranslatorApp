"""
Routes and views for the flask application.
"""

import subprocess
from datetime import datetime
from flask import render_template, jsonify
from TranslatorApp import app, Configuration, kaContent, subtitle, statistic, glossary, contributions, crowdin_pretranslate

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


@app.route('/health')
def health():
    """Health-check endpoint for deployment validation.

    Returns JSON with status, database connectivity, and git version.
    HTTP 200 if healthy, 503 if any check fails.
    No authentication required.
    """
    result = {'status': 'ok', 'db': 'unknown', 'version': 'unknown'}
    healthy = True

    # Database connectivity
    try:
        import pymysql
        conn = pymysql.connect(
            host=Configuration.dbHost,
            user=Configuration.dbUser,
            password=Configuration.dbPassword,
            database=Configuration.dbDatabase,
            connect_timeout=5
        )
        conn.cursor().execute('SELECT 1')
        conn.close()
        result['db'] = 'ok'
    except Exception as e:
        result['db'] = f'error: {type(e).__name__}'
        healthy = False

    # Git version hash
    try:
        git_hash = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            stderr=subprocess.DEVNULL, timeout=5
        ).decode().strip()
        result['version'] = git_hash
    except Exception:
        result['version'] = 'unavailable'

    status_code = 200 if healthy else 503
    return jsonify(result), status_code
