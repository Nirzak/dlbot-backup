import shutil, psutil
import signal
import pickle

from os import execl, path, remove
from sys import executable
import os
import time
import heroku3
from telegram.ext import CommandHandler
from bot import dispatcher, updater, botStartTime, HEROKU_API, HEROKU_APP
from bot.helper.ext_utils import fs_utils
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import *
from .helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time
from .helper.telegram_helper.filters import CustomFilters
from .modules import authorize, list, mirror_status, delete, music

import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

def stats(update, context):
    currentTime = get_readable_time((time.time() - botStartTime))
    total, used, free = shutil.disk_usage('.')
    total = get_readable_file_size(total)
    used = get_readable_file_size(used)
    free = get_readable_file_size(free)
    sent = get_readable_file_size(psutil.net_io_counters().bytes_sent)
    recv = get_readable_file_size(psutil.net_io_counters().bytes_recv)
    cpuUsage = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    stats = f'<b>Bot Uptime ⌚:</b> {currentTime}\n' \
            f'<b>Total disk space🗄️:</b> {total}\n' \
            f'<b>Used 🗃️:</b> {used}  ' \
            f'<b>Free 🗃️:</b> {free}\n\n' \
            f'📇Data Usage📇\n<b>Uploaded :</b> {sent}\n' \
            f'<b>Downloaded:</b> {recv}\n\n' \
            f'<b>CPU 🖥️:</b> {cpuUsage}% ' \
            f'<b>RAM ⛏️:</b> {memory}% ' \
            f'<b>Disk 🗄️:</b> {disk}%'
    sendMessage(stats, context.bot, update)

def start(update, context): 
    LOGGER.info('UID: {} - UN: {} - MSG: {}'.format(update.message.chat.id,update.message.chat.username,update.message.text))   
    if CustomFilters.authorized_user(update) or CustomFilters.authorized_chat(update):  
        if update.message.chat.type == "private" :  
            sendMessage(f"Hey <b>{update.message.chat.first_name}</b>. Welcome to <b>Music Mirror Bot</b>", context.bot, update) 
        else :  
            sendMessage("I'm alive :)", context.bot, update)    
    else :  
        sendMessage("Oops! not an authorized user.", context.bot, update)    


def restart(update, context):
    if HEROKU_API is not None and HEROKU_APP is not None:
        conn = heroku3.from_key(HEROKU_API)
        app = conn.apps()[HEROKU_APP]
        sendMessage("Heroku App found Restarting", context.bot, update)
        app.restart()
    else :
        sendMessage("Crashing the bot to restart", context.bot, update)
        os.kill(os.getpid(), signal.SIGTERM)  


def log(update, context):
    if HEROKU_API is not None and HEROKU_APP is not None:
        conn = heroku3.from_key(HEROKU_API)
        app = conn.apps()[HEROKU_APP]
        try:
            lin = int(context.args[0])
            logg = app.get_log(lines=lin)
            fil = open("heroku.txt", "w")
            fil.write(logg)
            fil.close()
            sendLogFile(context.bot, update,logtyp='Heroku')
        except IndexError:
            logg = app.get_log(lines=100)
            fil = open("heroku.txt", "w")
            fil.write(logg)
            fil.close()
            sendLogFile(context.bot, update,logtyp='Heroku')
    else:
        sendLogFile(context.bot, update)
        
def bot_help(update, context):  
    help_string_adm = f'''  
/{BotCommands.StartCommand} <b>: Alive or Not</b>   
/{BotCommands.MusicCommand} <b>[link]: Mirror any Tidal/Qobuz link</b>  
/{BotCommands.TarMusicCommand} <b>[link]: Mirror any Tidal/Qobuz Link & upload as .tar</b>  
/{BotCommands.StatusCommand} <b>: Shows a status of all the downloads</b>   
/{BotCommands.ListCommand} <b>[name]: Searches in the drive folder</b>  
/{BotCommands.deleteCommand} <b>[link]: Delete from drive[Only owner & sudo]</b>    
/{BotCommands.StatsCommand} <b>: Show Stats of the machine</b>  
/{BotCommands.RestartCommand} <b>: Restart bot[Only owner & sudo]</b>   
/{BotCommands.AuthorizeCommand} <b>: Authorize[Only owner & sudo]</b>   
/{BotCommands.UnAuthorizeCommand} <b>: Unauthorize[Only owner & sudo]</b>   
/{BotCommands.AuthorizedUsersCommand} <b>: authorized users[Only owner & sudo]</b>  
/{BotCommands.AddSudoCommand} <b>: Add sudo user[Only owner]</b>    
/{BotCommands.RmSudoCommand} <b>: Remove sudo users[Only owner]</b> 
/{BotCommands.LogCommand} <b>: Get log file[Only owner & sudo]</b>  

''' 
    help_string = f'''  
/{BotCommands.StartCommand} <b>: Alive or Not</b>   
/{BotCommands.MusicCommand} <b>[link]: Mirror any Tidal/Qobuz link</b>  
/{BotCommands.TarMusicCommand} <b>[link]: Mirror any Tidal/Qobuz Link & upload as .tar</b>  
/{BotCommands.StatusCommand} <b>: Shows a status of all the downloads</b>   
/{BotCommands.ListCommand} <b>[name]: Searches in the drive folder</b>  
/{BotCommands.StatsCommand} <b>: Show Stats of the machine</b>  

''' 
    if CustomFilters.sudo_user(update) or CustomFilters.owner_filter(update):   
        sendMessage(help_string_adm, context.bot, update)   
    else:   
        sendMessage(help_string, context.bot, update)


def main():
    fs_utils.start_cleanup()
    start_handler = CommandHandler(BotCommands.StartCommand, start,run_async=True)
    restart_handler = CommandHandler(BotCommands.RestartCommand, restart, filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True)
    help_handler = CommandHandler(BotCommands.HelpCommand, bot_help, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    stats_handler = CommandHandler(BotCommands.StatsCommand, stats, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    log_handler = CommandHandler(BotCommands.LogCommand, log, filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True, pass_args=True)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(restart_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(stats_handler)
    dispatcher.add_handler(log_handler)
    updater.start_polling()
    LOGGER.info("Yeah I'm running")
    signal.signal(signal.SIGINT, fs_utils.exit_clean_up)


main()
