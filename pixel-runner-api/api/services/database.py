import os
from typing import Any, Dict, List, Optional
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    # Fail silently or warning in server logs to prevent crash during Vercel build/import checks
    print("Warning: SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables are missing.")

# Initialize the Supabase client using the service role key to bypass RLS for backend tasks
supabase: Client = create_client(SUPABASE_URL or "", SUPABASE_SERVICE_KEY or "")

def get_active_config(config_type: str) -> Optional[Dict[str, Any]]:
    """Retrieve the active configuration for a given config_type from the pixel_runner.configs table."""
    try:
        response = supabase.schema("pixel_runner").table("configs")\
            .select("config_data")\
            .eq("config_type", config_type)\
            .eq("is_active", True)\
            .order("version", desc=True)\
            .limit(1)\
            .execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]["config_data"]
        return None
    except Exception as e:
        print(f"Error fetching active config {config_type}: {e}")
        return None

def get_config_versions(config_type: str) -> List[Dict[str, Any]]:
    """Retrieve all versions of a configuration from the pixel_runner.configs table."""
    try:
        response = supabase.schema("pixel_runner").table("configs")\
            .select("version, config_name, is_active, created_at")\
            .eq("config_type", config_type)\
            .order("version", desc=True)\
            .execute()
        return response.data or []
    except Exception as e:
        print(f"Error fetching config versions for {config_type}: {e}")
        return []

def insert_config(config_type: str, config_name: str, config_data: Dict[str, Any], is_active: bool = True) -> Dict[str, Any]:
    """Insert a new configuration version. Automatically deactivates old ones if is_active is True."""
    try:
        # Determine the next version number
        v_response = supabase.schema("pixel_runner").table("configs")\
            .select("version")\
            .eq("config_type", config_type)\
            .order("version", desc=True)\
            .limit(1)\
            .execute()
        
        next_version = 1
        if v_response.data and len(v_response.data) > 0:
            next_version = v_response.data[0]["version"] + 1

        if is_active:
            # Set all older ones to inactive
            supabase.schema("pixel_runner").table("configs")\
                .update({"is_active": False})\
                .eq("config_type", config_type)\
                .execute()

        new_config = {
            "config_type": config_type,
            "config_name": config_name,
            "config_data": config_data,
            "version": next_version,
            "is_active": is_active
        }

        response = supabase.schema("pixel_runner").table("configs")\
            .insert(new_config)\
            .execute()
        
        return response.data[0] if response.data else {}
    except Exception as e:
        print(f"Error inserting config: {e}")
        raise e

def insert_session(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """Insert or update a session in pixel_runner.sessions."""
    try:
        # We check if session_id exists. If so, update; otherwise insert.
        sess_id = session_data.get("session_id")
        if not sess_id:
            raise ValueError("session_id is required in session data")

        # Let's see if session exists
        existing = supabase.schema("pixel_runner").table("sessions")\
            .select("id")\
            .eq("session_id", sess_id)\
            .execute()

        if existing.data and len(existing.data) > 0:
            # Update
            db_id = existing.data[0]["id"]
            response = supabase.schema("pixel_runner").table("sessions")\
                .update(session_data)\
                .eq("id", db_id)\
                .execute()
        else:
            # Insert
            response = supabase.schema("pixel_runner").table("sessions")\
                .insert(session_data)\
                .execute()
        
        return response.data[0] if response.data else {}
    except Exception as e:
        print(f"Error inserting/updating session: {e}")
        raise e

def get_session_db_uuid(session_id: str) -> Optional[str]:
    """Get the internal database UUID id for a given session_id string."""
    try:
        response = supabase.schema("pixel_runner").table("sessions")\
            .select("id")\
            .eq("session_id", session_id)\
            .execute()
        if response.data and len(response.data) > 0:
            return response.data[0]["id"]
        return None
    except Exception as e:
        print(f"Error retrieving UUID for session_id {session_id}: {e}")
        return None

def insert_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Batch insert gameplay events into pixel_runner.events."""
    if not events:
        return []
    try:
        response = supabase.schema("pixel_runner").table("events")\
            .insert(events)\
            .execute()
        return response.data or []
    except Exception as e:
        print(f"Error inserting events: {e}")
        raise e

def insert_frame_samples(frame_samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Batch insert frame samples into pixel_runner.frame_samples."""
    if not frame_samples:
        return []
    try:
        response = supabase.schema("pixel_runner").table("frame_samples")\
            .insert(frame_samples)\
            .execute()
        return response.data or []
    except Exception as e:
        print(f"Error inserting frame samples: {e}")
        raise e

def get_recent_sessions(boss_key: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve the most recent sessions from pixel_runner.sessions, optionally filtered by boss_key."""
    try:
        query = supabase.schema("pixel_runner").table("sessions").select("*")
        if boss_key:
            query = query.eq("boss_key", boss_key)
        response = query.order("ended_at", desc=True).limit(limit).execute()
        return response.data or []
    except Exception as e:
        print(f"Error fetching recent sessions for boss_key {boss_key}: {e}")
        return []
