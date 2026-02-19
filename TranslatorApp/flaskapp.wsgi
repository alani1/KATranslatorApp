#!/usr/bin/python

#activate_this = '/var/www/vhosts/kadeutsch.org/TranslatorApp/TranslatorApp/venv/bin/activate_this.py'
#with open(activate_this) as file_:
#    exec(file_.read(), dict(__file__=activate_this))



import sys
import logging

logging.basicConfig(stream=sys.stderr)
sys.path.insert(0,"/var/www/vhosts/kadeutsch.org/TranslatorApp/TranslatorApp")

from TranslatorApp import app as application
# secret_key is set in TranslatorApp/__init__.py from Configuration.py

