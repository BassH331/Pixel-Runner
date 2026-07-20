import os
import json
import hashlib
from typing import Dict, Any, Tuple

class AudioValidationError(Exception):
    """Custom exception raised when player audio config validation fails."""
    pass

def calculate_file_hash(filepath: str) -> str:
    """Calculate SHA256 hash of a file."""
    if not os.path.exists(filepath):
        raise AudioValidationError(f"Audio asset file not found: {filepath}")
    sha256 = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
    except Exception as e:
        raise AudioValidationError(f"Failed to read file {filepath} for hashing: {e}")
    return sha256.hexdigest()

def calculate_config_hash(config_dict: Dict[str, Any]) -> str:
    """Calculate SHA256 hash of the configuration dictionary serialized as minified JSON."""
    serialized = json.dumps(config_dict, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

def generate_lock_data(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Generate the lock metadata dict for the given configuration."""
    config_hash = calculate_config_hash(config_dict)
    audio_hashes = {}
    
    # Hash all referenced sound files
    sounds = config_dict.get("sounds", {})
    for sound_name, relative_path in sounds.items():
        if relative_path:
            audio_hashes[relative_path] = calculate_file_hash(relative_path)
            
    return {
        "config_hash": config_hash,
        "audio_hashes": audio_hashes
    }

def save_config_and_lock(config_dict: Dict[str, Any], config_path: str, lock_path: str) -> None:
    """Save configuration JSON and its corresponding lock file."""
    # Ensure parent directories exist
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    
    # Generate lock first (verifies all files exist)
    lock_data = generate_lock_data(config_dict)
    
    # Save config
    with open(config_path, "w") as f:
        json.dump(config_dict, f, indent=4)
        
    # Save lock
    with open(lock_path, "w") as f:
        json.dump(lock_data, f, indent=4)

def verify_config_integrity(config_path: str, lock_path: str) -> Tuple[bool, str]:
    """
    Verify the configuration file matches the lockfile and no audio assets are missing or modified.
    Returns (True, "") if valid, or (False, "reason") if invalid.
    """
    if not os.path.exists(config_path):
        return False, f"Configuration file not found: {config_path}"
    if not os.path.exists(lock_path):
        return False, f"Lockfile not found: {lock_path}"
        
    try:
        with open(config_path, "r") as f:
            config_dict = json.load(f)
            
        with open(lock_path, "r") as f:
            lock_data = json.load(f)
    except Exception as e:
        return False, f"Failed to parse config or lockfile: {e}"
        
    # Verify config hash
    expected_config_hash = lock_data.get("config_hash")
    actual_config_hash = calculate_config_hash(config_dict)
    if expected_config_hash != actual_config_hash:
        return False, f"Configuration contents do not match the lockfile signature. Expected {expected_config_hash}, got {actual_config_hash}."
        
    # Verify each audio file hash
    expected_audio_hashes = lock_data.get("audio_hashes", {})
    sounds = config_dict.get("sounds", {})
    
    for sound_name, relative_path in sounds.items():
        if not relative_path:
            continue
        if relative_path not in expected_audio_hashes:
            return False, f"Audio file {relative_path} is referenced in config but missing in lockfile metadata."
        if not os.path.exists(relative_path):
            return False, f"Referenced audio file not found: {relative_path}"
            
        try:
            actual_hash = calculate_file_hash(relative_path)
        except AudioValidationError as e:
            return False, str(e)
            
        if actual_hash != expected_audio_hashes[relative_path]:
            return False, f"Audio file contents modified for {relative_path}. Expected {expected_audio_hashes[relative_path]}, got {actual_hash}."
            
    return True, ""
