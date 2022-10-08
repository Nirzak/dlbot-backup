
from telegram.ext import CommandHandler
from telegram import Bot, Update
from bot import Interval, DOWNLOAD_DIR, DOWNLOAD_STATUS_UPDATE_INTERVAL, dispatcher, LOGGER
from bot.helper.ext_utils.bot_utils import setInterval
from bot.helper.telegram_helper.message_utils import update_all_messages, sendMessage, sendStatusMessage
from .mirror import MirrorListener
from bot.helper.mirror_utils.download_utils.tidal_dl_download_helper import TidalDLHelper
from bot.helper.mirror_utils.download_utils.qobuz_dl_download_helper import QobuzDLHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
import threading
import requests
import re
import json
from bs4 import BeautifulSoup

def qobuzmetadata(qtype,qid):
    QOBUZAPI_URL = f"https://www.qobuz.com/api.json/0.2/{qtype}/get?{qtype}_id={qid}&app_id=712109809"
    resp = requests.get(QOBUZAPI_URL)
    if resp.status_code == requests.codes.ok:
        apiresp = resp.json()
        if qtype == "track":
            title = apiresp["title"].replace("/"," ")
            artist = apiresp["performer"]["name"]
            bit = str(apiresp["maximum_bit_depth"])
            samprate = str(apiresp["maximum_sampling_rate"])
            chan = str(apiresp["maximum_channel_count"])
            year = str(apiresp["album"]["release_date_original"].split("-")[0])
            if apiresp["hires"]:
                return f"{title} by {artist} ({year}) [Track] [{bit}Bit-{samprate}KHz] [{chan} Channels] [Hi-Res] [Qobuz-DL]"
            else:
                return f"{title} by {artist} ({year}) [Track] [{bit}Bit-{samprate}KHz] [{chan} Channels] [Lossless] [Qobuz-DL]"
        
        elif qtype == "album":
            title = apiresp["title"].replace("/"," ")
            artist = apiresp["artist"]["name"]
            disc = str(apiresp["media_count"])
            tracks = str(apiresp["tracks_count"])
            bit = str(apiresp["maximum_bit_depth"])
            samprate = str(apiresp["maximum_sampling_rate"])
            chan = str(apiresp["maximum_channel_count"])
            year = str(apiresp["release_date_original"].split("-")[0])
            if apiresp["hires"]:
                return f"{title} ({year}) by {artist} [Album] [{disc} Discs] [{tracks} Tracks] [{bit}Bit-{samprate}KHz] [{chan} Channels] [Hi-Res] [Qobuz-DL]"
            else:
                return f"{title} ({year}) by {artist} [Album] [{disc} Discs] [{tracks} Tracks] [{bit}Bit-{samprate}KHz] [{chan} Channels] [Lossless] [Qobuz-DL]"
        
        elif qtype == "playlist":
            title = apiresp["name"].replace("/"," ")
            owner = apiresp["owner"]["name"]
            tracks = str(apiresp["tracks_count"])
            return f"{title} by {owner} [Playlist] [{tracks} Tracks] [Qobuz-DL]"
        
        elif qtype == "artist":
            name = apiresp["name"].replace("/"," ")
            albums = str(apiresp["albums_count"])
            return f"{name} [Artist] [{albums} Albums] [Qobuz-DL]"

        elif qtype == "label":
            name = apiresp["name"].replace("/"," ")
            albums = str(apiresp["albums_count"])
            return f"{name} [Label] [{albums} Albums] [Qobuz-DL]"
        
        else:
            return None
    else:
        return None

def tidalmetadata(link):
    NotFound = 'TIDAL Browse - High Fidelity Music Streaming'
    tid =' on TIDAL'
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4505.0 Safari/537.36"}
    data=requests.get(link, headers=headers)
    bssoup = BeautifulSoup(data.content, 'lxml')
    try:
        title = bssoup.title.string
        if title == NotFound:
            return None
        else:
            if tid in title:
                return title.replace(tid,'')
    except:
        return None
def _music(bot: Bot, update: Update, args: list, isTar=False):
    try:
        link = args[0]
        if 'tidal.com' in link or 'play.qobuz' in link or 'open.qobuz' in link:
            if not re.match('(?:http|https)://', link):
                link = 'https://{}'.format(link)
        else:
            sendMessage(f'<code>Check the Link</code>\nfor more info type /{BotCommands.MusicCommand}',bot,update)
            return
    except IndexError:
        msg = f"/{BotCommands.MusicCommand} <b>[Tidal/Qobuz Link] [quality]</b>.\n\n"
        msg += f'<b>Tidal </b>\n'
        msg += f'Link can be <code>Track/Artist/Album/Video/Playlist</code>\n'
        msg += f'<b>Available Qualities :- </b> '
        msg += f'<code>Normal</code>,'+f'<code>High</code>,'+f'<code>HiFi</code>,'+f'<code>Master</code>'
        msg += f'\n<b>Note :- </b>\n Quality is optional (Default : <code>Master</code>)\n'
        msg += f'<b>Ex: </b>\n <code>/{BotCommands.MusicCommand} https://tidal.com/browse/track/111610009 Master</code> \n\n'
        msg += f'<b>Qobuz </b>\n'
        msg += f'Link can be <code>Track/Artist/Album/Playlist/Label</code>\n'
        msg += f'Link Should be from <code>play.qobuz.com</code> or <code>open.qobuz.com</code>\n'
        msg += f'\n<b>Available Qualities :-</b>\n'
        msg += f'<b>320Kbps- </b><code>320</code>\n'
        msg += f'<b>Lossless(16-Bit) - </b><code>16B</code>\n'
        msg += f'<b>24Bit(96Khz-) - </b><code>24B</code>\n'
        msg += f'<b>24Bit(96Khz+) - </b><code>24B+</code>\n'
        msg += f'\n<b>Note :- </b>Quality is optional (Default : <code>24B+</code>)\n'
        msg += f"\n<b>Ex:</b>\n<code>/{BotCommands.MusicCommand} https://play.qobuz.com/album/baemkikxzkj7b 320</code>"
        sendMessage(msg, bot, update)
        return
    
    if 'tidal.com' in link:
        regex = re.findall('([^\?]+)(\?.*)?', link)
        link = str(regex[0][0])
        types = link.split('/')
        try:
            tidalid = types[-1]
            tidaltype = types[-2]
        except IndexError:
            sendMessage(f'<code>Check the Link</code>\nfor more info type /{BotCommands.MusicCommand}',bot,update)
            return
        try:
          qual = args[1]
        except IndexError:
          qual = "Master"

        reply_to = update.message.reply_to_message
        if reply_to is not None:
            tag = reply_to.from_user.username
        else:
            tag = None

        title = tidalmetadata(link)
        name = f"{title} [{tidaltype.capitalize()}] [{qual}] [TIDAL-DL]"
        listener = MirrorListener(bot, update, isTar, tag)
        tdl = TidalDLHelper(listener)
        threading.Thread(target=tdl.add_download,args=(link, f'{DOWNLOAD_DIR}{listener.uid}', qual, tidalid, name)).start()
        sendStatusMessage(update, bot)
        if len(Interval) == 0:
            Interval.append(setInterval(DOWNLOAD_STATUS_UPDATE_INTERVAL, update_all_messages))
    elif 'play.qobuz' in link or 'open.qobuz' in link:
        regex = re.findall('([^\?]+)(\?.*)?', link)
        link = str(regex[0][0])
        types = link.split('/')
        try:
            qobuzid = types[-1]
            qobuztype = types[-2]
        except IndexError:
            sendMessage(f'<code>Check the Link</code>\nfor more info type /{BotCommands.MusicCommand}',bot,update)
            return
        name = qobuzmetadata(qobuztype,qobuzid)
        if name is not None:
            try:
              qual = args[1]
            except IndexError:
              qual = "24B+"
            reply_to = update.message.reply_to_message
            if reply_to is not None:
                tag = reply_to.from_user.username
            else:
                tag = None
            listener = MirrorListener(bot, update, isTar, tag)
            qdl = QobuzDLHelper(listener)
            threading.Thread(target=qdl.add_download,args=(link, f'{DOWNLOAD_DIR}{listener.uid}', qual, name, qobuzid)).start()
            sendStatusMessage(update, bot)
            if len(Interval) == 0:
                Interval.append(setInterval(DOWNLOAD_STATUS_UPDATE_INTERVAL, update_all_messages))
        else:
            sendMessage(f'<code>Check the Link</code>\nfor more info type /{BotCommands.MusicCommand}',bot,update)
            return

def MusicTar(update, context):
    _music(context.bot, update, context.args, True)


def Music(update, context):
    _music(context.bot, update, context.args)


mirror_handler = CommandHandler(BotCommands.MusicCommand, Music,
                                pass_args=True,
                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,run_async=True)
tar_mirror_handler = CommandHandler(BotCommands.TarMusicCommand, MusicTar,
                                    pass_args=True,
                                    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,run_async=True)
dispatcher.add_handler(mirror_handler)
dispatcher.add_handler(tar_mirror_handler)
