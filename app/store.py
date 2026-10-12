import sqlite3, threading
from pathlib import Path

class SignalStore:
    def __init__(self,path:str):
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.path=path; self.lock=threading.Lock()
        with self._db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS signals (signal_id TEXT PRIMARY KEY, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)')
    def _db(self): return sqlite3.connect(self.path)
    def claim(self, signal_id:str)->bool:
        with self.lock, self._db() as db:
            try:
                db.execute('INSERT INTO signals(signal_id) VALUES(?)',(signal_id,)); db.commit(); return True
            except sqlite3.IntegrityError: return False
