import sqlite3
import os
import logging
from datetime import datetime

class DatabaseLogger:
    def __init__(self, db_path="trade_logs.db"):
        self.db_path = db_path
        self.conn = None
        self._init_db()

    def _init_db(self):
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = self.conn.cursor()
            
            # 거래 로그 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trade_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    mode TEXT,
                    market TEXT,
                    code TEXT,
                    name TEXT,
                    signal TEXT,
                    ai_score REAL,
                    reason TEXT,
                    action TEXT,
                    price REAL,
                    qty INTEGER
                )
            ''')

            # 에러 로그 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS error_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    module TEXT,
                    error_msg TEXT
                )
            ''')
            
            self.conn.commit()
        except Exception as e:
            logging.error(f"Failed to initialize database: {e}")

    def log_trade(self, mode, market, code, name, signal, ai_score, reason, action, price=0.0, qty=0):
        if not self.conn:
            return
        try:
            timestamp = datetime.now().isoformat()
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO trade_history (timestamp, mode, market, code, name, signal, ai_score, reason, action, price, qty)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, mode, market, code, name, signal, ai_score, reason, action, price, qty))
            self.conn.commit()
        except Exception as e:
            logging.error(f"Failed to log trade to DB: {e}")

    def log_error(self, module, error_msg):
        if not self.conn:
            return
        try:
            timestamp = datetime.now().isoformat()
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO error_logs (timestamp, module, error_msg)
                VALUES (?, ?, ?)
            ''', (timestamp, module, error_msg))
            self.conn.commit()
        except Exception as e:
            logging.error(f"Failed to log error to DB: {e}")

    def close(self):
        if self.conn:
            self.conn.close()

# Global singleton
db_logger = DatabaseLogger()

# Setup standard logging alongside DB logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("system.log"),
        logging.StreamHandler()
    ]
)

def get_logger(name):
    return logging.getLogger(name)
