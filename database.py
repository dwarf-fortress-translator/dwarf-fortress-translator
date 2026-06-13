"""
Database operations for OCR Translator
Handles SQLite caching for translations and words
"""

import sqlite3
import logging
from config import DB_FILE, HISTORY_LIMIT
from utils import normalize_text, text_hash

log = logging.getLogger("ocr_translator")


def init_db():
    
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS translations (
            hash TEXT PRIMARY KEY,
            source TEXT,
            translated TEXT,
            favorite INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS word_cache (
            word_hash TEXT PRIMARY KEY,
            source_word TEXT,
            translated_word TEXT,
            usage_count INTEGER DEFAULT 1,
            last_used DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS phrase_composition (
            phrase_hash TEXT,
            word_hash TEXT,
            word_position INTEGER,
            FOREIGN KEY (phrase_hash) REFERENCES translations(hash),
            FOREIGN KEY (word_hash) REFERENCES word_cache(word_hash),
            PRIMARY KEY (phrase_hash, word_position)
        )
    """)

    conn.commit()
    conn.close()
    log.debug("Database initialized")


class TranslationCache:
    
    
    def __init__(self):
        self.db_file = DB_FILE
    
    def _get_connection(self):
        return sqlite3.connect(self.db_file)
    
    def get_cached_word(self, word: str):
        
        normalized = normalize_text(word)
        word_hash = text_hash(normalized)
        
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT translated_word FROM word_cache WHERE word_hash = ?", (word_hash,))
        row = cur.fetchone()
        
        if row:
            cur.execute(
                "UPDATE word_cache SET usage_count = usage_count + 1, last_used = CURRENT_TIMESTAMP WHERE word_hash = ?",
                (word_hash,)
            )
            conn.commit()
        
        conn.close()
        return row[0] if row else None
    
    def save_word_translation(self, source_word: str, translated_word: str):
        
        normalized = normalize_text(source_word)
        word_hash = text_hash(normalized)
        
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO word_cache 
            (word_hash, source_word, translated_word, usage_count)
            VALUES (?, ?, ?, COALESCE(
                (SELECT usage_count + 1 FROM word_cache WHERE word_hash = ?), 1
            ))
        """, (word_hash, source_word, translated_word, word_hash))
        conn.commit()
        conn.close()
    
    def get_cached_translation(self, text: str):
        
        h = text_hash(normalize_text(text))
        
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT translated FROM translations WHERE hash = ?", (h,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None
    
    def save_translation(self, text: str, translated: str, word_hashes=None):
        
        h = text_hash(normalize_text(text))
        
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO translations (hash, source, translated)
            VALUES (?, ?, ?)
        """, (h, text, translated))

        if word_hashes:
            for pos, word_hash in enumerate(word_hashes):
                if word_hash:
                    cur.execute("""
                        INSERT OR REPLACE INTO phrase_composition (phrase_hash, word_hash, word_position)
                        VALUES (?, ?, ?)
                    """, (h, word_hash, pos))

        conn.commit()
        conn.close()
    
    def toggle_favorite(self, source_text: str):
        
        h = text_hash(normalize_text(source_text))
        
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE translations
            SET favorite = CASE favorite WHEN 1 THEN 0 ELSE 1 END
            WHERE hash = ?
        """, (h,))
        conn.commit()
        conn.close()


    def _delete_by_source(self, source_text: str):
        
        h = text_hash(normalize_text(source_text))
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM translations WHERE hash = ?", (h,))
        conn.commit()
        conn.close()

    def _clear_all(self):
        
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM translations")
        conn.commit()
        conn.close()
    
    def get_history(self, search: str = ""):
        
        conn = self._get_connection()
        cur = conn.cursor()
        pattern = f"%{search}%"
        cur.execute(f"""
            SELECT source, translated, favorite, created_at
            FROM translations
            WHERE source LIKE ? OR translated LIKE ?
            ORDER BY favorite DESC, created_at DESC
            LIMIT {HISTORY_LIMIT}
        """, (pattern, pattern))
        rows = cur.fetchall()
        conn.close()
        return rows