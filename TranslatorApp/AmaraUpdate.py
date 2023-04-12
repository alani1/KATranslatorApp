import json
import pymysql
import requests
from datetime import datetime
import TranslatorApp.Configuration as Configuration

amaraAPI = Configuration.amaraAPI

def lookupYTID(amaraID):
    url = 'https://amara.org/api/videos/%s/' % amaraID
    headers = {'X-api-key': amaraAPI}
    response = requests.get(url,headers=headers).json()
    YTURL = response['all_urls'][0]
    YTID = YTURL.split('v=')[1]
    return YTID

dbConnection = None

def getDBConnection():

    global dbConnection
    if dbConnection == None:
        dbConnection = pymysql.connect(host=Configuration.dbHost,
                    user=Configuration.dbUser,
                    password=Configuration.dbPassword,
                    db=Configuration.dbDatabase,
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor)

    return dbConnection


def getDBObjects(YTid):

    dbConnection = getDBConnection()

    sql = "SELECT * FROM `ka-content` WHERE `youtube_id` = '%s'" % YTid
    with dbConnection.cursor() as cursor:
        cursor.execute(sql)
        result = cursor.fetchall()
    return result

def getKATranslatorName(amaraName):
    dbConnection = getDBConnection()
    sql = "SELECT wp_users.user_login as user FROM wp_users, wp_usermeta WHERE wp_usermeta.user_id = wp_users.ID AND wp_usermeta.meta_key='googleplus' AND wp_usermeta.meta_value='%s'" % amaraName
    
    cursor = dbConnection.cursor()
    cursor.execute(sql)
    result = cursor.fetchall()

    if (len(result) >0):
        return result[0]['user']
    else:
        return amaraName
    return amaraName

def doSQL(sql):
    dbConnection = getDBConnection()
    cursor = dbConnection.cursor()
    cursor.execute(sql)
    dbConnection.commit()

if __name__ == '__main__':
    limit = 100
    print("Update KADeutsch Content Database from last %s activities from Amara" % limit)

    #convert date in form 2023-04-10T18:06:18Z to 2023-04-10
    def convertDate(date):
        return date.split('T')[0]
    #
    

    #Activity Types
    #collab-auto-unassigned                         Unassigne user                                       -> Null
    #version-added (added a new revision)           ignore
    #collab-assign                                  assigned user to video with role e.g. 'subtitler'    -> Assigned
    #collab-reassign                                ""
    #collab-join                                    ignore
    #collab-leave                                   Unassigne user                                       -> Null
    #collab-unassign                                Unassigne user                                       -> Null
    
    #collab-state-change                            state_change 'endorse' by 'subtitler                 -> Translated
    
    #version-accepted                                    

    ignored = 0
    unknown = 0
    update = 0
    url = "https://amara.org/api/teams/khan-academy/activity/?language=de&limit=%s" % limit
    print(url)


    headers = {'X-api-key': amaraAPI} 
    response = requests.get(url,headers=headers).json()

    for stActivity in reversed(response["objects"]):

        video = stActivity["video"]
        date = stActivity["date"]
        

        if stActivity['type'] == 'collab-assign' or stActivity['type'] == 'collab-reassign':
            ytID = lookupYTID(video)
            db = getDBObjects(ytID)
            translator = getKATranslatorName(stActivity['assignee']['username'])
            
            #we only check status of the first object
            if len(db) > 0 and db[0]['translation_status'] == None and db[0]['translator'] == None:
                print('%s Video "%s" assigned to %s' % ( date, db[0]['original_title'], translator) )
                sql = "UPDATE `ka-content` SET `translation_status` = 'Assigned', `translator` = '%s', `translation_date` = '%s' WHERE `youtube_id` = '%s'" % ( translator, date.split('T')[0], ytID)
                doSQL(sql)
                update = update + 1

            else:
                print('%s Video "%s" already assigned to %s' % (date, db[0]['original_title'], translator) )

        elif stActivity['type'] == 'collab-auto-unassigned' or (stActivity['type'] == 'collab-unassign' and stActivity['role'] == 'subtitler'):
            ytID = lookupYTID(video)
            db = getDBObjects(ytID)
            translator = getKATranslatorName(stActivity['assignee']['username'])

            if len(db) > 0 and db[0]['translation_status'] == 'Assigned' and db[0]['translator'] == translator:
                print('%s Video "%s" unassigned from %s' % ( date, db[0]['original_title'], translator))
                sql = "UPDATE `ka-content` SET `translation_status` = NULL, `translator` = NULL, `translation_date` = NULL WHERE `youtube_id` = '%s'" % ytID
                doSQL(sql)
                update = update + 1

        #Change status to translated
        elif stActivity['type'] == 'collab-state-change' and stActivity['state_change'] == 'endorse' and stActivity['role'] == 'subtitler':
            ytID = lookupYTID(video)
            db = getDBObjects(ytID)
            translator = getKATranslatorName(stActivity['user']['username'])
            
            sql = "UPDATE `ka-content` SET `translation_status` = 'Translated', `translator` = '%s', `translation_date` = '%s' WHERE `youtube_id` = '%s'" % ( translator, date.split('T')[0], ytID)            
            if len(db) > 0 and db[0]['translation_status'] == 'Assigned' and db[0]['translator'] == translator:
                print('%s Video "%s" translated/endorsed by %s' % ( date, db[0]['original_title'], translator ))

                update = update + 1
                doSQL(sql)

            else:
                if ( not db[0]['translation_status'] == 'Translated' ):
                    print('%s Video "%s" translated/endorsed by %s' % ( date, db[0]['original_title'], translator ))
                    print('inconsistent state (%s,%s), still moving to Translated' % (db[0]['translation_status'], db[0]['translator']))
                    update = update + 1
                    doSQL(sql)
                else:
                    print('%s Video "%s" already in status Translated' % (date, db[0]['original_title']))

        #ignore these Activity Types
        elif stActivity['type'] == 'version-added' or stActivity['type'] == 'collab-join' or stActivity['type'] == 'collab-unassign' or stActivity['type'] == 'collab-state-change':           
            ignored = ignored + 1

        else:
            print("%s Unknown Activity: " + stActivity['type'])
            print(stActivity)
            unknown = unknown + 1

    print("Ignored %s activities" % ignored)
    print("Unknown %s activities" % unknown)
    print("Updated %s activities" % update)
