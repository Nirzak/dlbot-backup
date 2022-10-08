from .download_helper import DownloadHelper
import time
from bot import download_dict_lock, download_dict
from ..status_utils.tidal_dl_download_status import TidalDLDownloadStatus
import logging
import threading
import subprocess
import os

LOGGER = logging.getLogger(__name__)


class MyLogger:
    def __init__(self, obj):
        self.obj = obj

    def debug(self, msg):
        LOGGER.debug(msg)
        # Hack to fix changing changing extension
        match = re.search(r'.ffmpeg..Merging formats into..(.*?).$', msg)
        if match and not self.obj.is_playlist:
            self.obj.name = match.group(1)

    @staticmethod
    def warning(msg):
        LOGGER.warning(msg)

    @staticmethod
    def error(msg):
        LOGGER.error(msg)


class TidalDLHelper(DownloadHelper):
    def __init__(self, listener):
        super().__init__()
        self.__name = ""
        self.__start_time = time.time()
        self.__listener = listener
        self.__gid = ""
        self.opts = {
            'progress_hooks': [self.__onDownloadProgress],
            'logger': MyLogger(self),
            'usenetrc': True
        }
        self.__download_speed = 0
        self.download_speed_readable = ''
        self.downloaded_bytes = 0
        self.size = 0
        self.is_playlist = False
        self.last_downloaded = 0
        self.is_cancelled = False
        self.vid_id = ''
        self.__resource_lock = threading.RLock()
        self.processpid = None

    @property
    def download_speed(self):
        with self.__resource_lock:
            return self.__download_speed

    @property
    def gid(self):
        with self.__resource_lock:
            return self.__gid

    def __onDownloadProgress(self, d):
        if self.is_cancelled:
            raise ValueError("Cancelling Download..")
        if d['status'] == "finished":
            if self.is_playlist:
                self.last_downloaded = 0
        elif d['status'] == "downloading":
            with self.__resource_lock:
                self.__download_speed = d['speed']
                if self.is_playlist:
                    progress = d['downloaded_bytes'] / d['total_bytes']
                    chunk_size = d['downloaded_bytes'] - self.last_downloaded
                    self.last_downloaded = d['total_bytes'] * progress
                    self.downloaded_bytes += chunk_size
                    try:
                        self.progress = (self.downloaded_bytes / self.size) * 100
                    except ZeroDivisionError:
                        pass
                else:
                    self.download_speed_readable = d['_speed_str']
                    self.downloaded_bytes = d['downloaded_bytes']

    def __onDownloadStart(self):
        with download_dict_lock:
            download_dict[self.__listener.uid] = TidalDLDownloadStatus(self, self.__listener)

    def __onDownloadComplete(self):
        self.__listener.onDownloadComplete()

    def onDownloadError(self, error):
        self.processpid.terminate()
        self.__listener.onDownloadError(error)


    def __download(self, link, path):
        try:
            down = subprocess.run(["tidal-dl", "-l", link])
            self.processpid=down
            if self.is_cancelled:
                print("Nothing to do")
            else:
                if down.returncode == 0:
                    try:
                        os.rename(path+'/Tidal/',path+'/'+self.name+'/')
                        self.__onDownloadComplete()
                    except FileNotFoundError:
                        self.onDownloadError('Internal Error Occured')    
        except ValueError:
            LOGGER.info("Download Cancelled by User!")
            self.onDownloadError("Download Cancelled by User!")

    def add_download(self, link, path, qual, tidalid, name):
        try:
            self.name = name
            self.__onDownloadStart()
            LOGGER.info(f"Downloading with Tidal-DL: {link}")
            self.__gid = f"{tidalid}{self.__listener.uid}"
            pathset = subprocess.run(["tidal-dl", "-o", path+'/Tidal/']).returncode
            qualset = subprocess.run(["tidal-dl", "-q", qual]).returncode
            self.__download(link,path)
        except TypeError:
            self.onDownloadError('Cannot get the details from the link😐\nPlease check the Link')

    def cancel_download(self):
        self.is_cancelled = True
