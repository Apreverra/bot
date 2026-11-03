import logging
import time

from database import init_and_sync_db, get_all_tracks
from player import AudioEngine

## главный запуск
def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    logger = logging.getLogger("MAIN")
    
    ## база и плейлист
    init_and_sync_db("radio.db", "music")
    playlist = get_all_tracks("radio.db")
    
    if not playlist:
        logger.error("empty folder")
        return

    logger.info("tracks found: %d", len(playlist))

    ## запуск движка
    engine = AudioEngine(output_url="icecast://source:hackme@127.0.0.1:8000/radio.mp3")
    
    ## бесконечный цикл эфира
    logger.info("starting")
    try:
        while True:
            for track in playlist:
                engine.play_track(track)
                time.sleep(0.1) 
            
            logger.info("repeating")
                
    except KeyboardInterrupt:
        logger.info("shutdown")
    finally:
        engine.terminate()

if __name__ == "__main__":
    main()