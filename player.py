import subprocess
import logging
from typing import Optional
from database import Track
import urllib.request
import urllib.parse

## логи
logger = logging.getLogger(__name__)

## движок аудио
class AudioEngine:
    def __init__(self, output_url: str = "udp://127.0.0.1:12345"):
        self.output_url = output_url
        self.master_process: Optional[subprocess.Popen] = None
        self._start_master()

    ## постоянный эфир
    def _start_master(self) -> None:
        master_cmd = [
            "ffmpeg",
            "-y", "-hide_banner", "-loglevel", "error",
            "-f", "s16le", "-ar", "48000", "-ac", "2", "-i", "pipe:0",
            "-c:a", "libmp3lame", "-b:a", "192k",
            "-content_type", "audio/mpeg", # это кстати суперобязательно для айскаста
            "-f", "mp3", self.output_url
        ]
        logger.info("master ffmpeg: %s", self.output_url)
        self.master_process = subprocess.Popen(
            master_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=None
        )

    ## проигрывание файла
    def play_track(self, track: Track) -> bool:
        if not self.master_process or self.master_process.poll() is not None:
            self._start_master()

        self._update_metadata(track)

        ## воркер для декодирования
        worker_cmd = [
            "ffmpeg",
            "-re",  
            "-i", track.filepath,
            "-hide_banner", "-loglevel", "error",
            "-f", "s16le", "-ar", "48000", "-ac", "2", "pipe:1"
        ]

        logger.info("playing: %s", track.title)
        
        try:
            worker = subprocess.Popen(worker_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            chunk_size = 4096
            
            while True:
                chunk = worker.stdout.read(chunk_size)
                if not chunk:
                    break
                self.master_process.stdin.write(chunk)

            worker.wait()
            return True

        except Exception as e:
            logger.error("!!!error!!! %s: %s", track.title, e)
            return False
        finally:
            if 'worker' in locals() and worker.poll() is None:
                worker.kill()

    def _update_metadata(self, track: Track) -> None:
        try:            
            # login
            username = "admin"
            password = "hackme"
            host_port = 8000
            mountpoint = "/radio.mp3"

            # metadata gen
            artist = getattr(track, 'artist', '')
            title = track.title
            song_title = f"{artist} - {title}" if artist else title

            # icecast admin api
            params = urllib.parse.urlencode({
                'mode': 'updinfo',
                'mount': mountpoint,
                'song': song_title
            })
            
            api_url = f"http://127.0.0.1:{host_port}/admin/metadata?{params}"
            
            # http auth
            password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
            password_mgr.add_password(None, api_url, username, password)
            handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
            opener = urllib.request.build_opener(handler)
            
            # send
            with opener.open(api_url, timeout=2) as response:
                if response.status == 200:
                    logger.info("metadata updated: %s", song_title)
                else:
                    logger.warning("Icecast sent %s", response.status)
                    
        except Exception as e:
            logger.error("metadata update error: %s", e)

    ## остановка
    def terminate(self) -> None:
        if self.master_process and self.master_process.poll() is None:
            self.master_process.terminate()