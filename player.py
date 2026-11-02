import subprocess
import logging
from typing import Optional
from database import Track

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
            "-f", "mp3", self.output_url
        ]
        logger.info("master ffmpeg: %s", self.output_url)
        self.master_process = subprocess.Popen(
            master_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    ## проигрывание файла
    def play_track(self, track: Track) -> bool:
        if not self.master_process or self.master_process.poll() is not None:
            self._start_master()

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
            logger.error("Ошибка %s: %s", track.title, e)
            return False
        finally:
            if 'worker' in locals() and worker.poll() is None:
                worker.kill()

    ## остановка
    def shutdown(self) -> None:
        if self.master_process and self.master_process.poll() is None:
            self.master_process.terminate()