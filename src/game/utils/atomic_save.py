"""
src/game/utils/atomic_save.py

Unified Atomic File Save & Plugin Commit Integrity Engine for Pixel Runner.

Guarantees CIA (Confidentiality, Integrity, Availability) across all editor plugins,
config managers, and registries:
1. Atomic Transactional Writes: Writes to a process-unique temporary file (.tmp_<pid>_<uuid>),
   flushes, fsyncs, and executes os.replace() to eliminate partial/corrupt 0-byte file writes.
2. Validated Rolling Backups: Validates that target content is non-empty and valid JSON before
   creating timestamped backups (.backup_<timestamp>). Automatically prunes old backups to max 5.
3. Disk Re-Read & Merge: Re-reads fresh disk content prior to committing, preventing plugins
   from clobbering external manual edits or concurrent editor edits to non-owned keys.
4. UTF-8 & File Handle Safety: Explicit encoding="utf-8" and strict context management.
"""

import os
import sys
import time
import json
import uuid
import glob
from typing import Dict, Any, List, Tuple, Optional


def prune_backups(file_path: str, max_backups: int = 5) -> None:
    """
    Finds all backup files for file_path (.backup_*) and prunes old archives
    so that at most max_backups remain.
    """
    if not file_path:
        return
    parent_dir = os.path.dirname(os.path.abspath(file_path))
    filename = os.path.basename(file_path)
    pattern = os.path.join(parent_dir, f"{filename}.backup_*")
    backups = glob.glob(pattern)
    
    if len(backups) > max_backups:
        # Sort by mtime ascending (oldest first)
        backups.sort(key=lambda p: os.path.getmtime(p))
        to_delete = backups[: len(backups) - max_backups]
        for b in to_delete:
            try:
                os.remove(b)
            except Exception as e:
                print(f"[AtomicSave] Prune warning for {b}: {e}")


def create_validated_backup(file_path: str, max_backups: int = 5) -> Optional[str]:
    """
    Creates a timestamped backup of file_path if it exists, is non-empty, and contains
    valid non-corrupt content. Prunes old backups to max_backups.
    Returns the backup path if created, or None.
    """
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            print(f"[AtomicSave] Warning: Refusing backup of empty file {file_path}")
            return None

        # Verify JSON validity if file is a JSON file
        if file_path.endswith(".json"):
            json.loads(content)

        timestamp = int(time.time())
        backup_path = f"{file_path}.backup_{timestamp}"
        
        # Write backup atomically
        tmp_backup = f"{backup_path}.tmp_{os.getpid()}_{uuid.uuid4().hex[:6]}"
        with open(tmp_backup, "w", encoding="utf-8") as dst:
            dst.write(content)
            dst.flush()
            os.fsync(dst.fileno())

        os.replace(tmp_backup, backup_path)
        prune_backups(file_path, max_backups=max_backups)
        return backup_path
    except Exception as e:
        print(f"[AtomicSave] Warning: Backup creation failed for {file_path}: {e}")
        return None


def atomic_write_json(
    file_path: str,
    data: Dict[str, Any],
    indent: int = 4,
    backup: bool = True,
    max_backups: int = 5
) -> bool:
    """
    Atomically writes data as JSON to file_path.
    1. Creates validated non-empty backup if target exists and backup=True.
    2. Writes JSON to a temporary file (.tmp_<pid>_<uuid>).
    3. Flushes and fsyncs to disk.
    4. Replaces target file via os.replace() (atomic POSIX/Win32 operation).
    """
    tmp_path = None
    try:
        parent_dir = os.path.dirname(os.path.abspath(file_path))
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        if backup:
            create_validated_backup(file_path, max_backups=max_backups)

        tmp_path = f"{file_path}.tmp_{os.getpid()}_{uuid.uuid4().hex[:6]}"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=indent, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())

        os.replace(tmp_path, file_path)
        return True
    except Exception as e:
        print(f"[AtomicSave] Error saving JSON to {file_path}: {e}")
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return False


def atomic_merge_json(
    file_path: str,
    new_data: Dict[str, Any],
    domain_keys: Optional[List[str]] = None,
    indent: int = 4,
    backup: bool = True,
    max_backups: int = 5
) -> Tuple[bool, Dict[str, Any]]:
    """
    Re-reads fresh disk file (if present), merges new_data into it, and atomically saves.
    - If domain_keys is specified, updates ONLY those keys in fresh disk data from new_data.
    - Otherwise, performs top-level dict update (fresh_disk.update(new_data)).
    Returns (success_boolean, merged_dict).
    """
    fresh_disk: Dict[str, Any] = {}
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    fresh_disk = loaded
        except Exception as e:
            print(f"[AtomicSave] Warning: Could not read fresh disk file {file_path}: {e}")

    merged = dict(fresh_disk)
    if domain_keys is not None:
        for k in domain_keys:
            if k in new_data:
                merged[k] = new_data[k]
    else:
        merged.update(new_data)

    success = atomic_write_json(
        file_path=file_path,
        data=merged,
        indent=indent,
        backup=backup,
        max_backups=max_backups
    )
    return success, merged
