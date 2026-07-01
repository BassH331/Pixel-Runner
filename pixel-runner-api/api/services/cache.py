import os
import json
from typing import Any, Dict, Optional
from upstash_redis import Redis

UPSTASH_REDIS_REST_URL = os.environ.get("UPSTASH_REDIS_REST_URL")
UPSTASH_REDIS_REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")

# Initialize Redis with REST client. If credentials aren't set, we fall back to database directly.
redis_client: Optional[Redis] = None
if UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN:
    try:
        redis_client = Redis(url=UPSTASH_REDIS_REST_URL, token=UPSTASH_REDIS_REST_TOKEN)
    except Exception as e:
        print(f"Failed to initialize Upstash Redis: {e}")
else:
    print("Warning: UPSTASH_REDIS_REST_URL or UPSTASH_REDIS_REST_TOKEN variables are missing. Caching disabled.")

def get_cached_config(config_type: str) -> Optional[Dict[str, Any]]:
    """Retrieve config from Redis cache."""
    if not redis_client:
        return None
    try:
        key = f"pixel_runner:config:{config_type}"
        val = redis_client.get(key)
        if val:
            if isinstance(val, bytes):
                val = val.decode("utf-8")
            return json.loads(val)
    except Exception as e:
        print(f"Cache read error for {config_type}: {e}")
    return None

def set_cached_config(config_type: str, data: Dict[str, Any], ttl: int = 300) -> None:
    """Save config to Redis cache with a TTL (default 5 minutes)."""
    if not redis_client:
        return
    try:
        key = f"pixel_runner:config:{config_type}"
        redis_client.set(key, json.dumps(data), ex=ttl)
    except Exception as e:
        print(f"Cache write error for {config_type}: {e}")

def invalidate_cached_config(config_type: str) -> None:
    """Delete config from Redis cache to force reload on next request."""
    if not redis_client:
        return
    try:
        key = f"pixel_runner:config:{config_type}"
        redis_client.delete(key)
    except Exception as e:
        print(f"Cache invalidate error for {config_type}: {e}")
