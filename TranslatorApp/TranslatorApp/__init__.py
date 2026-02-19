"""The Flask application package for TranslatorApp."""

from flask import Flask
from flask_moment import Moment
from TranslatorApp import Configuration

app = Flask(__name__)
app.secret_key = Configuration.secret_key
moment = Moment(app)

import TranslatorApp.views
