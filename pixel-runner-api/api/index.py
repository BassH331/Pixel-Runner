import os
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Header, status
from pydantic import BaseModel, Field

# Local services
from .services import database as db
from .services import cache
from .services import difficulty

app = FastAPI(
    title="Pixel-Runner Cloud API",
    description="Serverless API backend for game configs and telemetry, with Redis caching and Supabase integration.",
    version="1.0.0"
)

API_WRITE_SECRET = os.environ.get("API_WRITE_SECRET")

# ─────────────────────────────────────────────────────────────────────────
# Pydantic Schemas for Requests
# ─────────────────────────────────────────────────────────────────────────

class ConfigPayload(BaseModel):
    config_name: str = "default"
    config_data: Dict[str, Any]
    is_active: bool = True

class SessionPayload(BaseModel):
    session_id: str
    boss_key: Optional[str] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    active_combat_duration_seconds: Optional[float] = None
    total_frames: Optional[int] = None
    average_fps: Optional[float] = None
    player_damage_taken: Optional[float] = None
    boss_damage_taken: Optional[float] = None
    player_hits_received: Optional[int] = None
    boss_hits_received: Optional[int] = None
    boss_attacks: Optional[int] = None
    successful_boss_attacks: Optional[int] = None
    boss_spell_casts: Optional[int] = None
    projectile_hits: Optional[int] = None
    projectile_misses: Optional[int] = None
    boss_defeated: Optional[bool] = None
    average_horizontal_distance: Optional[float] = None
    average_vertical_distance: Optional[float] = None
    average_player_boss_distance: Optional[float] = None
    player_defend_frames: Optional[int] = None
    player_standing_frames: Optional[int] = None
    player_jumps: Optional[int] = None
    player_side_swaps: Optional[int] = None
    total_active_combat_frames: Optional[int] = None
    files_parsed: Optional[List[str]] = None

class EventItem(BaseModel):
    session_id: str
    timestamp_ms: int
    event_type: str
    event_data: Dict[str, Any] = Field(default_factory=dict)

class FrameSampleItem(BaseModel):
    session_id: str
    timestamp_ms: int
    frame_number: int
    fps: float
    world_distance: float
    player: Optional[Dict[str, Any]] = None
    boss: Optional[Dict[str, Any]] = None
    active_entities: int = 0

# ─────────────────────────────────────────────────────────────────────────
# Helper to Validate Write Access
# ─────────────────────────────────────────────────────────────────────────
def verify_write_access(auth_secret: Optional[str]):
    if not API_WRITE_SECRET:
        # Default behavior: if no write secret is set, block writes for safety
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server API_WRITE_SECRET environment variable is not configured."
        )
    if auth_secret != API_WRITE_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid write authorization secret."
        )

# ─────────────────────────────────────────────────────────────────────────
# Health Endpoint
# ─────────────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health_check():
    """Verify backend connectivity to Supabase and Upstash Redis."""
    status_db = "disconnected"
    status_cache = "disconnected"
    
    # Check DB
    try:
        if db.supabase:
            status_db = "connected"
    except Exception:
        pass

    # Check Cache
    try:
        if cache.redis_client:
            cache.redis_client.ping()
            status_cache = "connected"
    except Exception:
        pass

    return {
        "status": "healthy",
        "database": status_db,
        "cache": status_cache
    }

# ─────────────────────────────────────────────────────────────────────────
# Config Retrieval & Management Endpoints
# ─────────────────────────────────────────────────────────────────────────
@app.get("/api/configs/{config_type}")
def get_config(config_type: str):
    """Retrieve the active configuration, checking cache first, then Supabase."""
    # 1. Try cache
    cached = cache.get_cached_config(config_type)
    if cached:
        return cached

    # 2. Try DB
    db_config = db.get_active_config(config_type)
    if db_config is not None:
        # Save to cache
        cache.set_cached_config(config_type, db_config)
        return db_config

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Configuration of type '{config_type}' not found."
    )

@app.get("/api/configs/{config_type}/versions")
def get_config_versions(config_type: str):
    """List all versions of a configuration type."""
    versions = db.get_config_versions(config_type)
    return versions

@app.get("/api/difficulty/{boss_key}")
def get_difficulty_recommendation(boss_key: str, limit: int = 20):
    """Return an aggregated difficulty recommendation for a boss type, computed
    from recent telemetry sessions across all players. Always returns 200 --
    falls back to BASELINE_CONFIG with confidence "none" if there's no data yet,
    so the client can always safely apply the response."""
    cached = cache.get_cached_difficulty(boss_key)
    if cached:
        return cached

    rows = db.get_recent_sessions(boss_key=boss_key, limit=limit)
    session_dicts = [difficulty.row_to_evaluation_dict(r) for r in rows]
    manager = difficulty.DifficultyManager()
    evaluation = manager.evaluate_sessions(session_dicts)

    recommended = evaluation.get("recommended_difficulty", "None")
    if recommended == "None":
        config = difficulty.DifficultyManager.BASELINE_CONFIG
    else:
        config = manager.get_preset_config(recommended)

    result = {
        "boss_key": boss_key,
        "recommended_difficulty": recommended,
        "confidence": evaluation.get("confidence", "none"),
        "valid_session_count": evaluation.get("valid_session_count", 0),
        "config": config,
    }
    cache.set_cached_difficulty(boss_key, result)
    return result

@app.post("/api/configs/{config_type}", status_code=status.HTTP_201_CREATED)
def create_config(
    config_type: str,
    payload: ConfigPayload,
    x_api_write_secret: Optional[str] = Header(None)
):
    """Insert a new config version and invalidate cached values."""
    verify_write_access(x_api_write_secret)
    
    # Insert config into DB
    result = db.insert_config(
        config_type=config_type,
        config_name=payload.config_name,
        config_data=payload.config_data,
        is_active=payload.is_active
    )
    
    # Invalidate cache
    cache.invalidate_cached_config(config_type)
    
    return {
        "message": "Config saved successfully",
        "version": result.get("version"),
        "is_active": result.get("is_active")
    }

# ─────────────────────────────────────────────────────────────────────────
# Telemetry Ingestion Endpoints
# ─────────────────────────────────────────────────────────────────────────
@app.post("/api/telemetry/session")
def post_session(payload: SessionPayload):
    """Save or update play session telemetry metrics."""
    try:
        res = db.insert_session(payload.model_dump(exclude_unset=True))
        return {"status": "success", "id": res.get("id"), "session_id": res.get("session_id")}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to save session: {e}"
        )

@app.post("/api/telemetry/events")
def post_events(payload: List[EventItem]):
    """Batch upload gameplay telemetry events."""
    if not payload:
        return {"status": "success", "inserted": 0}
        
    try:
        # Cache of session_id string -> database UUID
        session_uuid_map: Dict[str, str] = {}
        db_events = []
        
        for item in payload:
            sess_str = item.session_id
            if sess_str not in session_uuid_map:
                uuid_val = db.get_session_db_uuid(sess_str)
                if not uuid_val:
                    # If the session doesn't exist yet, insert a basic placeholder session
                    placeholder = db.insert_session({"session_id": sess_str})
                    uuid_val = placeholder.get("id")
                session_uuid_map[sess_str] = uuid_val
            
            db_events.append({
                "session_id": session_uuid_map[sess_str],
                "timestamp_ms": item.timestamp_ms,
                "event_type": item.event_type,
                "event_data": item.event_data
            })
            
        res = db.insert_events(db_events)
        return {"status": "success", "inserted": len(res)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to upload events: {e}"
        )

@app.post("/api/telemetry/frames")
def post_frames(payload: List[FrameSampleItem]):
    """Batch upload frame sample telemetry snapshots."""
    if not payload:
        return {"status": "success", "inserted": 0}

    try:
        # Cache of session_id string -> database UUID
        session_uuid_map: Dict[str, str] = {}
        db_frames = []

        for item in payload:
            sess_str = item.session_id
            if sess_str not in session_uuid_map:
                uuid_val = db.get_session_db_uuid(sess_str)
                if not uuid_val:
                    # Insert a placeholder session
                    placeholder = db.insert_session({"session_id": sess_str})
                    uuid_val = placeholder.get("id")
                session_uuid_map[sess_str] = uuid_val

            # Resolve Player fields from deserialized client dict
            player_state = None
            player_position = None
            player_velocity = None
            player_health = None
            player_is_invincible = False
            player_is_attacking = False

            if item.player:
                player_state = item.player.get("state")
                player_position = item.player.get("position") # list of 4 ints or None
                player_velocity = item.player.get("velocity") # list of 2 floats or None
                player_health = item.player.get("health")
                player_is_invincible = item.player.get("is_invincible", False)
                player_is_attacking = item.player.get("is_attacking", False)

            # Resolve Boss fields
            boss_state = None
            boss_position = None
            boss_health = None
            boss_mana = None

            if item.boss:
                boss_state = item.boss.get("state")
                # Make sure boss position is converted properly
                boss_pos_raw = item.boss.get("position")
                # Sometimes boss position can be list of [x, y, w, h], let's keep it consistent
                boss_position = boss_pos_raw
                boss_health = item.boss.get("health")
                boss_mana = item.boss.get("mana")

            db_frames.append({
                "session_id": session_uuid_map[sess_str],
                "timestamp_ms": item.timestamp_ms,
                "frame_number": item.frame_number,
                "fps": item.fps,
                "world_distance": item.world_distance,
                "player_state": player_state,
                "player_position": player_position,
                "player_velocity": player_velocity,
                "player_health": player_health,
                "player_is_invincible": player_is_invincible,
                "player_is_attacking": player_is_attacking,
                "boss_state": boss_state,
                "boss_position": boss_position,
                "boss_health": boss_health,
                "boss_mana": boss_mana,
                "active_entities_count": item.active_entities
            })

        res = db.insert_frame_samples(db_frames)
        return {"status": "success", "inserted": len(res)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to upload frame samples: {e}"
        )
