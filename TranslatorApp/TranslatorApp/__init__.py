"""
The flask application package.
"""

from flask import Flask
app = Flask(__name__)

import TranslatorApp.views, TranslatorApp.subtitle

app.register_blueprint(subtitle.bp)
