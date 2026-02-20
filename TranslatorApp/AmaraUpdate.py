import json
import requests
import datetime
import math
import re
import argparse
import TranslatorApp.Configuration as Configuration
from DBModule import getDBConnection

# Timeout (seconds) for all outbound HTTP requests
API_TIMEOUT = 30

amaraAPI = Configuration.amaraAPI


def lookupYTID(amaraID):
    """Convert an Amara video ID to a YouTube video ID."""
    url = 'https://amara.org/api/videos/%s/' % amaraID
    headers = {'X-api-key': amaraAPI}
    response = requests.get(url, headers=headers, timeout=API_TIMEOUT).json()
    YTURL = response['all_urls'][0]
    YTID = YTURL.split('v=')[1]
    return YTID

# Shared DB connection — opened once, reused throughout the run
_dbConnection = None

def _getDB():
    """Return a shared DB connection, opening one if needed."""
    global _dbConnection
    if _dbConnection is None or not _dbConnection.open:
        _dbConnection = getDBConnection()
    return _dbConnection


def getDBObjects(YTid):
    """Look up a video in ka-content by YouTube ID (parameterized query)."""
    conn = _getDB()
    sql = "SELECT * FROM `ka-content` WHERE `youtube_id` = %s"
    with conn.cursor() as cursor:
        cursor.execute(sql, (YTid,))
        result = cursor.fetchall()
    return result


def getKATranslatorName(amaraName):
    """Map an Amara username to the WordPress user_login (parameterized query)."""
    conn = _getDB()
    sql = (
        "SELECT wp_users.user_login AS user "
        "FROM wp_users "
        "INNER JOIN wp_usermeta ON wp_usermeta.user_id = wp_users.ID "
        "WHERE wp_usermeta.meta_key = 'googleplus' AND wp_usermeta.meta_value = %s"
    )
    with conn.cursor() as cursor:
        cursor.execute(sql, (amaraName,))
        result = cursor.fetchall()
    if len(result) > 0:
        return result[0]['user']
    return amaraName


def postDiscordTranslateMessage(db, stActivity):
    """Send a Discord embed when a video is translated."""
    url = Configuration.discordWebhookURL
    headers = {'Content-Type': 'application/json'}

    try:
        amaraUser = requests.get(stActivity['user']['uri'], headers={'X-api-key': amaraAPI}, timeout=API_TIMEOUT).json()
        amaraVideo = requests.get(stActivity['video_uri'], headers={'X-api-key': amaraAPI}, timeout=API_TIMEOUT).json()
    except Exception as e:
        print(f"[WARN] Discord message skipped — Amara API error: {e}")
        return

    username = stActivity['user']['username']
    userUrl = "https://www.kadeutsch.org/TranslatorApp/contribution/" + username
    title = db['translated_title']

    embed = {
        "title": "hat die Untertitel von \"%s\" übersetzt." % title,
        "url": userUrl,
        "description": "Danke @%s! Bitte helft den Untertitel zu kontrollieren." % username,
        "color": 3447003,
        "thumbnail": {"url": amaraUser.get('avatar', '')},
        "author": {"name": username, "url": userUrl},
        "image": {"url": amaraVideo.get('thumbnail', '')},
    }

    data = {"embeds": [embed]}
    try:
        requests.post(url, headers=headers, data=json.dumps(data), timeout=API_TIMEOUT)
    except Exception as e:
        print(f"[WARN] Discord webhook failed: {e}")


def doSQL(sql, params=None):
    """Execute a parameterized write query and commit."""
    conn = _getDB()
    with conn.cursor() as cursor:
        cursor.execute(sql, params)
    conn.commit()


def convertDate(date):
    """Extract YYYY-MM-DD from an ISO timestamp like 2023-04-10T18:06:18Z."""
    return date.split('T')[0]


def processActivity(stActivity):
    """Process a single Amara activity entry. Returns 'update', 'ignored', or 'unknown'."""
    video = stActivity["video"]
    date = stActivity["date"]
    activity_type = stActivity['type']
    role = stActivity.get('role', '')

    # ── Assign / Reassign (subtitler) ────────────────────────────────
    if activity_type in ('collab-assign', 'collab-reassign') and role == 'subtitler':
        ytID = lookupYTID(video)
        db = getDBObjects(ytID)
        if len(db) == 0:
            return 'ignored'

        translator = getKATranslatorName(stActivity['assignee']['username'])
        row = db[0]

        if row['translation_status'] is None:
            print('%s Video "%s" subtitler assigned to %s' % (date, row['original_title'], translator))
            doSQL(
                "UPDATE `ka-content` SET `translation_status` = 'Assigned', "
                "`translator` = %s, `translation_date` = %s "
                "WHERE `youtube_id` = %s",
                (translator, convertDate(date), ytID)
            )
            return 'update'
        elif row['translation_status'] == 'Assigned' and row['translator'] != translator:
            # Reassigned to a different subtitler — update the translator name
            print('%s Video "%s" subtitler reassigned from %s to %s' % (date, row['original_title'], row['translator'], translator))
            doSQL(
                "UPDATE `ka-content` SET `translator` = %s, `translation_date` = %s "
                "WHERE `youtube_id` = %s",
                (translator, convertDate(date), ytID)
            )
            return 'update'
        else:
            print('%s Video "%s" subtitler already assigned to %s' % (date, row['original_title'], translator))
            return 'ignored'

    # ── Assign / Reassign (reviewer) ─────────────────────────────────
    elif activity_type in ('collab-assign', 'collab-reassign') and role == 'reviewer':
        ytID = lookupYTID(video)
        db = getDBObjects(ytID)
        if len(db) == 0:
            return 'ignored'

        reviewer = getKATranslatorName(stActivity['assignee']['username'])
        row = db[0]

        if row.get('reviewer') != reviewer:
            print('%s Video "%s" reviewer assigned to %s' % (date, row['original_title'], reviewer))
            doSQL(
                "UPDATE `ka-content` SET `reviewer` = %s "
                "WHERE `youtube_id` = %s",
                (reviewer, ytID)
            )
            return 'update'
        else:
            print('%s Video "%s" reviewer already assigned to %s' % (date, row['original_title'], reviewer))
            return 'ignored'

    # ── Unassign (subtitler) ─────────────────────────────────────────
    elif activity_type == 'collab-auto-unassigned' or \
         (activity_type == 'collab-unassign' and role == 'subtitler'):
        ytID = lookupYTID(video)
        db = getDBObjects(ytID)
        if len(db) == 0:
            return 'ignored'

        translator = getKATranslatorName(stActivity['assignee']['username'])
        row = db[0]

        if row['translation_status'] == 'Assigned':
            print('%s Video "%s" subtitler unassigned from %s' % (date, row['original_title'], translator))
            doSQL(
                "UPDATE `ka-content` SET `translation_status` = NULL, "
                "`translator` = NULL, `translation_date` = NULL "
                "WHERE `youtube_id` = %s",
                (ytID,)
            )
            return 'update'
        else:
            print('%s Video "%s" subtitler unassign ignored (status=%s)' % (date, row['original_title'], row['translation_status']))
            return 'ignored'

    # ── Unassign (reviewer) ──────────────────────────────────────────
    elif activity_type == 'collab-unassign' and role == 'reviewer':
        ytID = lookupYTID(video)
        db = getDBObjects(ytID)
        if len(db) == 0:
            return 'ignored'

        reviewer = getKATranslatorName(stActivity['assignee']['username'])
        row = db[0]

        print('%s Video "%s" reviewer unassigned from %s' % (date, row['original_title'], reviewer))
        doSQL(
            "UPDATE `ka-content` SET `reviewer` = NULL "
            "WHERE `youtube_id` = %s",
            (ytID,)
        )
        return 'update'

    # ── Endorsed by subtitler → Translated ───────────────────────────
    elif activity_type == 'collab-state-change' and \
         stActivity.get('state_change') == 'endorse' and stActivity.get('role') == 'subtitler':
        ytID = lookupYTID(video)
        db = getDBObjects(ytID)
        if len(db) == 0:
            return 'ignored'

        translator = getKATranslatorName(stActivity['user']['username'])
        row = db[0]

        if row['translation_status'] == 'Translated':
            print('%s Video "%s" already in status Translated' % (date, row['original_title']))
            return 'ignored'

        msg = '%s Video "%s" translated/endorsed by @%s' % (date, row['original_title'], translator)
        print(msg)

        if row['translation_status'] != 'Assigned' or row['translator'] != translator:
            print('  inconsistent state (status=%s, translator=%s), still moving to Translated' % (
                row['translation_status'], row['translator']))

        doSQL(
            "UPDATE `ka-content` SET `translation_status` = 'Translated', "
            "`translator` = %s, `translation_date` = %s "
            "WHERE `youtube_id` = %s",
            (translator, convertDate(date), ytID)
        )
        try:
            postDiscordTranslateMessage(row, stActivity)
        except Exception as e:
            print(f"  [WARN] Discord notification failed: {e}")
        return 'update'

    # ── Endorsed by reviewer → Approved ──────────────────────────────
    elif activity_type == 'collab-state-change' and \
         stActivity.get('state_change') == 'endorse' and stActivity.get('role') == 'reviewer':
        ytID = lookupYTID(video)
        db = getDBObjects(ytID)
        if len(db) == 0:
            return 'ignored'

        reviewer = getKATranslatorName(stActivity['user']['username'])
        row = db[0]

        msg = '%s Video "%s" reviewed by @%s' % (date, row['original_title'], reviewer)
        print(msg)

        doSQL(
            "UPDATE `ka-content` SET `translation_status` = 'Approved', "
            "`reviewer` = %s, `review_date` = %s "
            "WHERE `youtube_id` = %s",
            (reviewer, convertDate(date), ytID)
        )
        return 'update'

    # ── Ignored activity types ───────────────────────────────────────
    elif activity_type in ('version-added', 'collab-join',
                           'collab-state-change', 'collab-leave'):
        return 'ignored'

    # ── Unknown ──────────────────────────────────────────────────────
    else:
        print("Unknown Activity: %s" % activity_type)
        print(stActivity)
        return 'unknown'


def parseDuration(value):
    """Parse a human-friendly duration string into a timedelta.

    Supported formats:
        30m   = 30 minutes
        3h    = 3 hours  (default when no unit given)
        7d    = 7 days
        2w    = 2 weeks

    A plain number without a unit is treated as hours for backwards compat.
    """
    m = re.fullmatch(r'(\d+(?:\.\d+)?)\s*([mhdw])?', value.strip().lower())
    if not m:
        raise argparse.ArgumentTypeError(
            f"Invalid duration '{value}'. Use e.g. 30m, 3h, 7d, 2w")
    amount = float(m.group(1))
    unit = m.group(2) or 'h'
    if unit == 'm':
        return datetime.timedelta(minutes=amount)
    elif unit == 'h':
        return datetime.timedelta(hours=amount)
    elif unit == 'd':
        return datetime.timedelta(days=amount)
    elif unit == 'w':
        return datetime.timedelta(weeks=amount)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Sync Amara subtitle activity to ka-content database"
    )
    parser.add_argument(
        '--since', type=parseDuration, default='3h',
        help="How far back to look. Examples: 30m, 3h, 7d, 2w (default: 3h)"
    )
    args = parser.parse_args()

    current_datetime = datetime.datetime.now()
    since = current_datetime - args.since

    ignored = 0
    unknown = 0
    update = 0

    url = "https://amara.org/api/teams/khan-academy/activity/?limit=100&language=de&after=%sZ" % since.isoformat()
    print(url)

    headers = {'X-api-key': amaraAPI}

    try:
        response = requests.get(url, headers=headers, timeout=API_TIMEOUT).json()
    except Exception as e:
        print(f"[ERROR] Failed to fetch activity: {e}")
        exit(1)

    total = response['meta']['total_count']
    print("Update KADeutsch Content Database with %s activities since %s from Amara" % (total, since.isoformat()))

    if total == 0:
        print("No activities found.")
        exit(0)

    # Start from the last page and walk backwards
    lastOffset = math.floor(total / 100) * 100
    url = url + "&offset=%s" % lastOffset
    fetchMore = True

    while fetchMore:
        print(url)
        try:
            response = requests.get(url, headers=headers, timeout=API_TIMEOUT).json()
        except Exception as e:
            print(f"[ERROR] Failed to fetch page: {e}")
            break

        if response['meta']['offset'] == 0:
            fetchMore = False
        else:
            url = response['meta']['previous']

        for stActivity in reversed(response["objects"]):
            try:
                result = processActivity(stActivity)
            except Exception as e:
                print(f"[ERROR] Failed to process activity: {e}")
                print(f"  Activity: {stActivity.get('type', '?')} / video={stActivity.get('video', '?')}")
                unknown += 1
                continue

            if result == 'update':
                update += 1
            elif result == 'unknown':
                unknown += 1
            else:
                ignored += 1

    print("---")
    print("Ignored %s activities" % ignored)
    print("Unknown %s activities" % unknown)
    print("Updated %s activities" % update)
