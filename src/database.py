import sqlite3
import json
import time
import os
from datetime import datetime

class DatabaseHandler:
    def __init__(self, db_path="data/bot_data.db"):
        # Ensure data directory exists
        # Assuming run from project root, data/ should be in root
        self.db_path = os.path.join(os.getcwd(), db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Trades Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL, -- ENTRY/EXIT
                direction TEXT DEFAULT 'LONG',
                price REAL,
                amount REAL,
                timestamp INTEGER,
                pnl_pct REAL,
                features TEXT, -- JSON string of indicators
                strategy_score REAL,
                status TEXT DEFAULT 'CLOSED'
            )
        ''')

        # Logs Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT,
                message TEXT,
                timestamp INTEGER
            )
        ''')
        
        # Daily Stats Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY, -- YYYY-MM-DD
                total_pnl REAL DEFAULT 0.0,
                trade_count INTEGER DEFAULT 0,
                win_count INTEGER DEFAULT 0,
                loss_count INTEGER DEFAULT 0
            )
        ''')
        
        self.create_indexes(cursor)
        
        conn.commit()
        conn.close()

    def create_indexes(self, cursor):
        """Creates performance indexes"""
        # Trades Table Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_pnl ON trades(pnl_pct)")
        
        # Logs Table Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level)")

    def log_message(self, level, message):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO logs (level, message, timestamp) VALUES (?, ?, ?)', 
                           (level, message, int(time.time())))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"DB Log Error: {e}")

    def add_trade(self, symbol, action, price, amount=0, pnl_pct=0, features=None, score=0, status="CLOSED"):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            features_json = json.dumps(features) if features else "{}"
            
            cursor.execute('''
                INSERT INTO trades (symbol, action, direction, price, amount, timestamp, pnl_pct, features, strategy_score, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (symbol, action, 'LONG', price, amount, int(time.time()), pnl_pct, features_json, score, status))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"DB Trade Error: {e}")

    def get_logs(self, limit=100):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT timestamp, level, message FROM logs ORDER BY timestamp DESC LIMIT ?', (limit,))
            rows = cursor.fetchall()
            conn.close()
            return rows
        except Exception:
            return []

    def get_trades(self, limit=100):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?', (limit,))
            cols = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            conn.close()
            return [dict(zip(cols, row)) for row in rows]
        except Exception:
            return []
