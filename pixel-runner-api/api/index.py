import os
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Header, status
from pydantic import BaseModel, Field

# Local services
from .services import database as db
from .services import cache
from .services import difficulty
from .services import kimi_service

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
    session_id: str = Field(..., max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    boss_key: Optional[str] = Field(None, max_length=64)
    started_at: Optional[str] = Field(None, max_length=64)
    ended_at: Optional[str] = Field(None, max_length=64)
    duration_seconds: Optional[float] = Field(None, ge=0.0, le=86400.0)
    active_combat_duration_seconds: Optional[float] = Field(None, ge=0.0, le=86400.0)
    total_frames: Optional[int] = Field(None, ge=0, le=10000000)
    average_fps: Optional[float] = Field(None, ge=0.0, le=1000.0)
    player_damage_taken: Optional[float] = Field(None, ge=0.0, le=100000.0)
    boss_damage_taken: Optional[float] = Field(None, ge=0.0, le=100000.0)
    player_hits_received: Optional[int] = Field(None, ge=0, le=100000)
    boss_hits_received: Optional[int] = Field(None, ge=0, le=100000)
    boss_attacks: Optional[int] = Field(None, ge=0, le=100000)
    successful_boss_attacks: Optional[int] = Field(None, ge=0, le=100000)
    boss_spell_casts: Optional[int] = Field(None, ge=0, le=100000)
    projectile_hits: Optional[int] = Field(None, ge=0, le=100000)
    projectile_misses: Optional[int] = Field(None, ge=0, le=100000)
    boss_defeated: Optional[bool] = None
    average_horizontal_distance: Optional[float] = Field(None, ge=-100000.0, le=1000000.0)
    average_vertical_distance: Optional[float] = Field(None, ge=-100000.0, le=1000000.0)
    average_player_boss_distance: Optional[float] = Field(None, ge=0.0, le=1000000.0)
    player_defend_frames: Optional[int] = Field(None, ge=0, le=10000000)
    player_standing_frames: Optional[int] = Field(None, ge=0, le=10000000)
    player_jumps: Optional[int] = Field(None, ge=0, le=100000)
    player_side_swaps: Optional[int] = Field(None, ge=0, le=100000)
    total_active_combat_frames: Optional[int] = Field(None, ge=0, le=10000000)
    files_parsed: Optional[List[str]] = Field(None, max_length=50)

class EventItem(BaseModel):
    session_id: str = Field(..., max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    timestamp_ms: int = Field(..., ge=0)
    event_type: str = Field(..., max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    event_data: Dict[str, Any] = Field(default_factory=dict)

class FrameSampleItem(BaseModel):
    session_id: Optional[str] = Field(None, max_length=64)
    timestamp_ms: Optional[int] = Field(None, ge=0)
    timestamp: Optional[int] = Field(None, ge=0)  # alias used by game client
    frame_number: Optional[int] = Field(None, ge=0)
    fps: Optional[float] = Field(None, ge=0.0, le=1000.0)
    world_distance: float = Field(0.0, ge=-100000.0, le=1000000.0)
    player: Optional[Dict[str, Any]] = None
    boss: Optional[Dict[str, Any]] = None
    active_entities: int = Field(0, ge=0, le=10000)

class AiDirectorPayload(BaseModel):
    session_id: Optional[str] = Field(None, max_length=64)
    boss_key: Optional[str] = Field(None, max_length=64)
    current_phase: int = Field(1, ge=1, le=10)
    frames: List[FrameSampleItem] = Field(default_factory=list, max_length=60)

# ─────────────────────────────────────────────────────────────────────────
# Helper to Validate Write Access
# ─────────────────────────────────────────────────────────────────────────
def verify_write_access(auth_secret: Optional[str], required: bool = True):
    secret = os.environ.get("API_WRITE_SECRET") or API_WRITE_SECRET
    if not secret:
        # No secret configured — allow all local dev traffic through
        return
    if not required:
        return
    if auth_secret != secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid write authorization secret."
        )

# ─────────────────────────────────────────────────────────────────────────
# Health Endpoint
# ─────────────────────────────────────────────────────────────────────────
# Health Endpoint
# ─────────────────────────────────────────────────────────────────────────
@app.get("/health")
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
@app.get("/configs/{config_type}")
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

@app.get("/configs/{config_type}/versions")
@app.get("/api/configs/{config_type}/versions")
def get_config_versions(config_type: str):
    """List all versions of a configuration type."""
    versions = db.get_config_versions(config_type)
    return versions

@app.get("/difficulty/{boss_key}")
@app.get("/api/difficulty/{boss_key}")
def get_difficulty_recommendation(boss_key: str, limit: int = 20):
    """Return an aggregated difficulty recommendation for a boss type, computed
    from recent telemetry sessions across all players. Always returns 200 --
    falls back to BASELINE_CONFIG with confidence "none" if there's no data yet,
    so the client can always safely apply the response."""
    try:
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
    except Exception as e:
        print(f"Error in difficulty endpoint: {e}")
        return {
            "boss_key": boss_key,
            "recommended_difficulty": "None",
            "confidence": "none",
            "valid_session_count": 0,
            "config": difficulty.DifficultyManager.BASELINE_CONFIG,
        }

@app.post("/configs/{config_type}", status_code=status.HTTP_201_CREATED)
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
@app.post("/telemetry/session")
@app.post("/api/telemetry/session")
def post_session(
    payload: SessionPayload,
    x_api_write_secret: Optional[str] = Header(None)
):
    """Save or update play session telemetry metrics."""
    verify_write_access(x_api_write_secret)
    try:
        res = db.insert_session(payload.model_dump(exclude_unset=True))
        return {"status": "success", "id": res.get("id"), "session_id": res.get("session_id")}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to save session: {e}"
        )

@app.post("/telemetry/events")
@app.post("/api/telemetry/events")
def post_events(
    payload: List[EventItem],
    x_api_write_secret: Optional[str] = Header(None)
):
    """Batch upload gameplay telemetry events."""
    verify_write_access(x_api_write_secret)
    if not payload:
        return {"status": "success", "inserted": 0}
    if len(payload) > 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Payload array exceeds maximum event batch limit of 50 items."
        )
        
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to upload events: {e}"
        )

@app.post("/telemetry/frames")
@app.post("/api/telemetry/frames")
def post_frames(
    payload: List[FrameSampleItem],
    x_api_write_secret: Optional[str] = Header(None)
):
    """Batch upload frame sample telemetry snapshots."""
    verify_write_access(x_api_write_secret)
    if not payload:
        return {"status": "success", "inserted": 0}
    if len(payload) > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Payload array exceeds maximum frame sample batch limit of 100 items."
        )

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


@app.post("/telemetry/ai-director")
@app.post("/api/telemetry/ai-director")
def post_ai_director(
    payload: AiDirectorPayload,
    x_api_write_secret: Optional[str] = Header(None)
):
    """Analyze live frame telemetry stream and return real-time AI director directives."""
    verify_write_access(x_api_write_secret)
    try:
        payload_dict = payload.model_dump()
        directive = kimi_service.evaluate_telemetry_directive(payload_dict)
    except Exception as e:
        print(f"[AI Director fallback] {e}")
        directive = kimi_service.generate_fallback_directive({})
    return {"status": "success", "directive": directive}

