
import TranslatorApp.Configuration as Configuration
import pymysql

# DB Module

        
# Connect to the database
connection = pymysql.connect(host=Configuration.dbHost,
            user=Configuration.dbUser,
            password=Configuration.dbPassword,
            db=Configuration.dbDatabase,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor)


def getDBConnection():    
    return connection
