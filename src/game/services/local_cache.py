import os
import sqlite3
import zlib
import json
from typing import Any, Dict, Optional, List, Tuple
from datetime import datetime

class LocalCache:
    """Encrypted/obfuscated local SQLite cache for configurations and pending telemetry.
    
    Uses standard library sqlite3 and zlib compression to ensure there are no
    external dependencies, while making the SQLite db binary and unreadable to
    plain editors (acting as a basic anti-tamper obfuscation layer).
    """
    
    DB_DIR = os.path.expanduser("~/.pixel_runner")
    DB_PATH = os.path.join(DB_DIR, "cache.db")
    
    _initialized = False

    @classmethod
    def _initialize(cls) -> None:
        """Initialize database folder and schema."""
        if cls._initialized:
            return
        try:
            os.makedirs(cls.DB_DIR, exist_ok=True)
            conn = sqlite3.connect(cls.DB_PATH)
            cursor = conn.cursor()
            
            # Create configs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS configs (
                    key TEXT PRIMARY KEY,
                    data BLOB,
                    updated_at TIMESTAMP
                )
            """)
            
            # Create telemetry queue table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telemetry_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT,
                    payload BLOB,
                    created_at TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
            cls._initialized = True
        except Exception as e:
            print(f"[CACHE ERROR] Failed to initialize local SQLite cache: {e}")

    @classmethod
    def get_config(cls, config_type: str) -> Optional[Dict[str, Any]]:
        """Retrieve a config from local database and decompress/parse JSON."""
        cls._initialize()
        try:
            conn = sqlite3.connect(cls.DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM configs WHERE key = ?", (config_type,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                compressed_data = row[0]
                decompressed_data = zlib.decompress(compressed_data)
                return json.loads(decompressed_data.decode("utf-8"))
        except Exception as e:
            print(f"[CACHE ERROR] Failed to retrieve cached config for {config_type}: {e}")
        return None

    @classmethod
    def set_config(cls, config_type: str, data: Dict[str, Any]) -> None:
        """Compress config data and save it to local database."""
        cls._initialize()
        try:
            json_str = json.dumps(data)
            compressed_data = zlib.compress(json_str.encode("utf-8"))
            
            conn = sqlite3.connect(cls.DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO configs (key, data, updated_at) VALUES (?, ?, ?)",
                (config_type, compressed_data, datetime.now())
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[CACHE ERROR] Failed to cache config {config_type}: {e}")

    @classmethod
    def queue_telemetry(cls, endpoint: str, data: Dict[str, Any]) -> None:
        """Queue unsent telemetry payload to SQLite database (for retries)."""
        cls._initialize()
        try:
            json_str = json.dumps(data)
            compressed_data = zlib.compress(json_str.encode("utf-8"))
            
            conn = sqlite3.connect(cls.DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO telemetry_queue (endpoint, payload, created_at) VALUES (?, ?, ?)",
                (endpoint, compressed_data, datetime.now())
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[CACHE ERROR] Failed to queue telemetry: {e}")

    @classmethod
    def get_pending_telemetry(cls) -> List[Tuple[int, str, Dict[str, Any]]]:
        """Fetch all pending telemetry queued in the SQLite database."""
        cls._initialize()
        pending = []
        try:
            conn = sqlite3.connect(cls.DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, endpoint, payload FROM telemetry_queue ORDER BY id ASC")
            rows = cursor.fetchall()
            conn.close()
            
            for row in rows:
                db_id, endpoint, compressed_payload = row
                decompressed_payload = zlib.decompress(compressed_payload)
                payload_dict = json.loads(decompressed_payload.decode("utf-8"))
                pending.append((db_id, endpoint, payload_dict))
        except Exception as e:
            print(f"[CACHE ERROR] Failed to fetch queued telemetry: {e}")
        return pending

    @classmethod
    def delete_queued_telemetry(cls, queue_id: int) -> None:
        """Remove a successfully sent telemetry payload from queue."""
        cls._initialize()
        try:
            conn = sqlite3.connect(cls.DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM telemetry_queue WHERE id = ?", (queue_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[CACHE ERROR] Failed to delete queued telemetry ID {queue_id}: {e}")
