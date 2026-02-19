"""User authentication and permission management via WordPress database and cookies."""

from TranslatorApp import Configuration
import pymysql
from flask import request


class User(object):
    """Represents an authenticated user with role-based permissions.
    
    Loads user identity from WordPress cookies and resolves permissions
    from the WordPress wp_users and wp_usermeta database tables.
    """

    def __init__(self, dbConnection):
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
        """Returns True if the user has administrator privileges (level >= 10)."""
        return self.user_level >= 10

    def isContributor(self):
        """Returns True if the user has contributor or higher privileges (level > 0)."""
        return self.user_level > 0
        
    def loadRoleFromDB(self):
        """Load user role and permission level from WordPress database.
        
        Queries wp_users to verify the user exists, then loads wp_user_level
        from wp_usermeta to determine the permission level.
        Level 10 = administrator, Level 1+ = contributor, Level 0 = subscriber.
        """
        if not self.name:
            return

        cursor = self.dbConnection.cursor()
        try:
            # Load user from WordPress users table (parameterized query)
            sql = "SELECT * FROM `wp_users` WHERE user_login = %s"
            cursor.execute(sql, (self.name,))

            # Return if no user found
            if cursor.rowcount == 0:
                return

            result = dict(cursor.fetchone())

            # Load permission level from wp_usermeta (parameterized query)
            ID = result['ID']
            permSQL = "SELECT * FROM wp_usermeta WHERE user_id = %s AND meta_key = 'wp_user_level'"
            cursor.execute(permSQL, (ID,))

            if cursor.rowcount == 0:
                return

            result = dict(cursor.fetchone())
            self.user_level = int(result['meta_value'])

            if self.user_level >= 10:
                self.role = 'administrator'
            elif self.user_level >= 1:
                self.role = 'contributor'
            else:
                self.role = 'subscriber'
        finally:
            cursor.close()

    def checkUserCookie(self):
        """Check for WordPress login cookie and extract the username.
        
        Looks for a 'wordpress_logged_in_*' cookie, parses the username
        from the first pipe-delimited field.
        
        Note: This should be made more secure by validating the HMAC hash
        values in the cookie fields against the WordPress salt/key.
        
        Returns:
            bool: True if a valid login cookie was found, False otherwise.
        """
        for cookie in request.cookies:
            if cookie[:20] == 'wordpress_logged_in_':
                cookieFields = request.cookies.get(cookie).replace('%7C', '|').split('|')
                self.name = cookieFields[0]
                self.role = ''
                return True

        return False