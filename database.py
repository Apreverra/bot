import sqlite3
import logging
from pathlib import Path
from dataclasses import dataclass
import mutagen

## логи
logger = logging.getLogger(__name__)

@dataclass
class Track:
    id: int
    filepath: str
    title: str

## база данных и сканер
def init_and_sync_db(db_path: str = "radio.db", music_dir: str = "music") -> None:
    music_path = Path(music_dir)
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        ## таблица трэков
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filepath TEXT UNIQUE NOT NULL,
                title TEXT
            );
        """)
        
        if not music_path.exists():
            logger.error("Папка %s не найдена", music_path)
            return

        ## сканируем музыку
        for filepath in music_path.rglob('*.mp3'):
            try:
                audio = mutagen.File(filepath, easy=True)
                title = audio.get('title', [filepath.stem])[0]
            except Exception:
                title = filepath.stem

            try:
                cursor.execute(
                    "INSERT INTO tracks (filepath, title) VALUES (?, ?)", 
                    (str(filepath.resolve()), title)
                )
                logger.info("new track: %s", title)
            except sqlite3.IntegrityError:
                pass
        
        conn.commit()

## список всех трэков
def get_all_tracks(db_path: str = "radio.db") -> list[Track]:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, filepath, title FROM tracks ORDER BY filepath ASC")
        rows = cursor.fetchall()
        
    return [Track(id=r[0], filepath=r[1], title=r[2]) for r in rows]