
from TranslatorApp import Configuration
import pymysql
from flask import request

class User(object):
    def __init__(self,dbConnection):
        self.dbConnection = dbConnection
        self.name = ''
        self.role = ''
        self.user_level = 0

        if Configuration.mode == 'dev':
            self.name = Configuration.devUser
            self.role = 'administrator'
            self.user_level = 10
        
        # Loads the UserName from Cookie
        self.checkUserCookie()
        self.loadRoleFromDB()

    def isAdmin(self):
        return self.user_level >= 10

    def isContributor(self):
        #print("isContributor : %i" % self.user_level)
        return self.user_level > 0
        
    def loadRoleFromDB(self):
        #Load UserName From Database
        sql = "select * from %s.`wp_users` where user_login='%s'" % (Configuration.dbDatabase, self.name)
        cursor = self.dbConnection.cursor()
        cursor.execute(sql)

        #return if no user found
        if (cursor.rowcount == 0):
            return

        result = dict(cursor.fetchone())

        #To be finished get the UserID, then load the permissions from wp_usermetadata in wp_capabilities and wp_user_level (Level 10 = administrator)
        ID = result['ID']
        permSQL = "select * from wp_usermeta where user_id='%s' and meta_key='wp_user_level'" % ID
        cursor.execute(permSQL)
        result = dict(cursor.fetchone())
        self.user_level = int(result['meta_value'])

        if (self.user_level >= 10):
            self.role = 'administrator'
        elif (self.user_level >= 1):
            self.role = 'contributor'
        else:
            self.role = self.user_level 

    #Note: This should be made more secure by validating the Hash Values in the Fields
    def checkUserCookie(self):
        #Function checks if the UserCookie exists and loads permission from DB
        for cookie in request.cookies:
            #Check if the cookie matches a substring
            if (cookie[:20] == 'wordpress_logged_in_'):
                #explode value by |
                #Replace escaped pipesymbol
                cookieFields = request.cookies.get(cookie).replace('%7C','|').split('|')
                self.name = cookieFields[0]
                self.role = ''
                return True

        return False