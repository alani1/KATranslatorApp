import csv

import TranslatorApp.Configuration as Configuration
from DBModule import getDBConnection
import urllib





if __name__ == '__main__':


    connection = getDBConnection()
    updateCnt = 0

    
    try:
        with connection.cursor() as cursor:

            # Download the TSV file from a URL
            url = 'https://storage.googleapis.com/public-content-export-data/de-export-recent.tsv'
            urllib.request.urlretrieve(url, 'de-export-recent.tsv')

            print('New Export Downloaded from Translation Portal')
            updateCnt = 0
            insertCnt = 0

            # Read the TSV file
            with open('de-export-recent.tsv', newline='', encoding='utf-8') as tsvfile:
                reader = csv.DictReader(tsvfile, delimiter='\t')
                i=0
                # Loop through each row in the TSV file
                for row in reader:

                    # Check if the row already exists in the database
                    select_query = "SELECT * FROM `ka-content` WHERE id='%s' AND lesson='%s'" % (row['id'], row['lesson'])
                    cursor.execute(select_query)
                    result = cursor.fetchone()

                    # If the row exists, check if any fields have changed
                    if result:
                        update_fields = []
                        for field in row:
                            if result[field] != row[field]:
                                update_fields.append((field, row[field]))

                        if update_fields:
                            updateCnt = updateCnt + 1

                            update_query = "UPDATE `ka-content` SET " + ", ".join(["{}=%s".format(field) for field, value in update_fields]) + " WHERE id=%s AND lesson=%s"
                            cursor.execute(update_query, [value for field, value in update_fields] + [row['id'], row['lesson']])

                    # If the row doesn't exist, insert it into the database
                    else:
                        print("Adding new content: " + row['id'] + " " + row['lesson'] + " " + row['original_title'])
                        insertCnt = insertCnt + 1

                        insert_query = "INSERT INTO `ka-content` (" + ", ".join(row.keys()) + ") VALUES (" + ", ".join(["%s"] * len(row.keys())) + ")"
                        cursor.execute(insert_query, list(row.values()))

                    i=i+1
                    if i%1000 == 0:
                        print("Processed %d rows" % i)

            # Mark rows as removed which don't exist in the file
            
            # Select all rows which are marked as deleted
            #select_removed_query = "SELECT * FROM `ka-content` WHERE deleted=True"
            #cursor.execute(select_removed_query)
            #result = cursor.fetchall()

            # Loop through each row which is marked as deleted
            # for row in result:
            # Check if the row exists in the file



        # Commit changes to the database
        connection.commit()

    finally:
        print("Updated %d rows, inserted %d rows" % (updateCnt, insertCnt))
        
        connection.close()
