import os
import json
import pytest
from src.game.audio.audio_lock import (
    calculate_file_hash,
    calculate_config_hash,
    generate_lock_data,
    save_config_and_lock,
    verify_config_integrity,
    AudioValidationError
)

def test_calculate_file_hash_missing():
    with pytest.raises(AudioValidationError):
        calculate_file_hash("nonexistent_file.wav")

def test_calculate_file_hash_success(tmp_path):
    temp_file = tmp_path / "test_sound.wav"
    temp_file.write_bytes(b"dummy audio data")
    
    file_hash = calculate_file_hash(str(temp_file))
    assert len(file_hash) == 64  # SHA256 length

def test_calculate_config_hash():
    config1 = {"sounds": {"sfx": "a.wav"}, "states": {}}
    config2 = {"states": {}, "sounds": {"sfx": "a.wav"}}  # Different order
    
    hash1 = calculate_config_hash(config1)
    hash2 = calculate_config_hash(config2)
    
    assert hash1 == hash2

def test_save_and_verify_integrity(tmp_path):
    config_file = tmp_path / "config.json"
    lock_file = tmp_path / "config.lock"
    
    sound1 = tmp_path / "sound1.wav"
    sound1.write_bytes(b"sound 1 data")
    sound2 = tmp_path / "sound2.wav"
    sound2.write_bytes(b"sound 2 data")
    
    config = {
        "sounds": {
            "key1": str(sound1),
            "key2": str(sound2)
        },
        "states": {
            "ATTACK_SMASH": {
                "3": "key1"
            }
        }
    }
    
    # Save config and lock
    save_config_and_lock(config, str(config_file), str(lock_file))
    
    assert os.path.exists(config_file)
    assert os.path.exists(lock_file)
    
    # Verify success
    valid, reason = verify_config_integrity(str(config_file), str(lock_file))
    assert valid
    assert reason == ""
    
    import copy
    # Modify config content slightly
    modified_config = copy.deepcopy(config)
    modified_config["states"]["ATTACK_SMASH"]["3"] = "key2"
    with open(config_file, "w") as f:
        json.dump(modified_config, f, indent=4)
        
    valid, reason = verify_config_integrity(str(config_file), str(lock_file))
    assert not valid
    assert "contents do not match" in reason
    
    # Restore config (it's untouched now), but modify sound1 file content
    with open(config_file, "w") as f:
        json.dump(config, f, indent=4)
    sound1.write_bytes(b"modified sound 1 data")
    
    valid, reason = verify_config_integrity(str(config_file), str(lock_file))
    assert not valid
    assert "contents modified" in reason

    
    # Restore sound1 file content, but delete sound2 file
    sound1.write_bytes(b"sound 1 data")
    sound2.unlink()
    
    valid, reason = verify_config_integrity(str(config_file), str(lock_file))
    assert not valid
    assert "not found" in reason
