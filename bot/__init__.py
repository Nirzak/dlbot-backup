import logging
import os
import threading
import time
import random
import string
import telegram.ext as tg
from dotenv import load_dotenv
from telegraph import Telegraph
import socket
import faulthandler
faulthandler.enable()

import psycopg2 
from psycopg2 import Error  
from telegraph import Telegraph

socket.setdefaulttimeout(600)

botStartTime = time.time()
if os.path.exists('log.txt'):
    with open('log.txt', 'r+') as f:
        f.truncate(0)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('log.txt'), logging.StreamHandler()],
                    level=logging.INFO)

load_dotenv('config.env')

Interval = []


def getConfig(name: str):
    return os.environ[name]

        
def mktable():  
    try:    
        conn = psycopg2.connect(DB_URI) 
        cur = conn.cursor() 
        sql = "CREATE TABLE users (uid bigint, sudo boolean DEFAULT FALSE);"    
        cur.execute(sql)    
        conn.commit()   
        LOGGER.info("Table Created!")   
    except Error as e:  
        LOGGER.error(e) 
        exit(1)

LOGGER = logging.getLogger(__name__)

try:
    if bool(getConfig('_____REMOVE_THIS_LINE_____')):
        logging.error('The README.md file there to be read! Exiting now!')
        exit()
except KeyError:
    pass


DOWNLOAD_DIR = None
BOT_TOKEN = None

download_dict_lock = threading.Lock()
status_reply_dict_lock = threading.Lock()
# Key: update.effective_chat.id
# Value: telegram.Message
status_reply_dict = {}
# Key: update.message.message_id
# Value: An object of Status
download_dict = {}
# Stores list of users and chats the bot is authorized to use in
AUTHORIZED_CHATS = set()
SUDO_USERS = set()

try:
    BOT_TOKEN = getConfig('BOT_TOKEN')
    DB_URI = getConfig('DATABASE_URL')
    parent_id = getConfig('GDRIVE_FOLDER_ID')
    DOWNLOAD_DIR = getConfig('DOWNLOAD_DIR')
    if DOWNLOAD_DIR[-1] != '/' or DOWNLOAD_DIR[-1] != '\\':
        DOWNLOAD_DIR = DOWNLOAD_DIR + '/'
    DOWNLOAD_STATUS_UPDATE_INTERVAL = int(getConfig('DOWNLOAD_STATUS_UPDATE_INTERVAL'))
    OWNER_ID = int(getConfig('OWNER_ID'))
    AUTO_DELETE_MESSAGE_DURATION = int(getConfig('AUTO_DELETE_MESSAGE_DURATION'))
except KeyError as e:
    LOGGER.error("One or more env variables missing! Exiting now")
    exit(1)

try:
    conn = psycopg2.connect(DB_URI)
    cur = conn.cursor()
    sql = "SELECT * from users;"
    cur.execute(sql)
    rows = cur.fetchall()  #returns a list ==> (uid, sudo)
    for row in rows:
        AUTHORIZED_CHATS.add(row[0])
        if row[1]:
            SUDO_USERS.add(row[0])
    print("Connected to DB")  
except psycopg2.DatabaseError as error :
    LOGGER.error(f"Error : {error}")
    exit(1)
finally:
    #closing database connection.
    if(conn):
        cur.close()
        conn.close()       


#Generate Telegraph Token
sname = ''.join(random.SystemRandom().choices(string.ascii_letters, k=8))
LOGGER.info("Generating Telegraph Token using '" + sname + "' name")
telegraph = Telegraph()
telegraph.create_account(short_name=sname)
telegraph_token = telegraph.get_access_token()
LOGGER.info("Telegraph Token Generated: '" + telegraph_token + "'")

try:
    INDEX_URL = getConfig('INDEX_URL')
    if len(INDEX_URL) == 0:
        INDEX_URL = None
except KeyError:
    INDEX_URL = None
try:
    IS_TEAM_DRIVE = getConfig('IS_TEAM_DRIVE')
    if IS_TEAM_DRIVE.lower() == 'true':
        IS_TEAM_DRIVE = True
    else:
        IS_TEAM_DRIVE = False
except KeyError:
    IS_TEAM_DRIVE = False

try:
    USE_SERVICE_ACCOUNTS = getConfig('USE_SERVICE_ACCOUNTS')
    if USE_SERVICE_ACCOUNTS.lower() == 'true':
        USE_SERVICE_ACCOUNTS = True
    else:
        USE_SERVICE_ACCOUNTS = False
except KeyError:
    USE_SERVICE_ACCOUNTS = False

try:
    HEROKU_API = getConfig('HEROKU_API')
    HEROKU_APP = getConfig('HEROKU_APP')
    if len(HEROKU_API) == 0 or len(HEROKU_APP)==0:
        raise KeyError
except KeyError:
    HEROKU_API = None
    HEROKU_APP = None

updater = tg.Updater(token=BOT_TOKEN,use_context=True)
bot = updater.bot
dispatcher = updater.dispatcher
