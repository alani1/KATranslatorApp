
import TranslatorApp.Configuration as Configuration
import pymysql

# DB Module

        
# Connect to the database
connection = None

def getDBConnection():  
    
    if (connection == None):
        connection = pymysql.connect(host=Configuration.dbHost,
            user=Configuration.dbUser,
            password=Configuration.dbPassword,
            db=Configuration.dbDatabase,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor)

    return connection

def closeDBConnection():
    connection.close()
    connection = None