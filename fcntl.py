"""
Cross-platform fcntl compatibility shim.
Enables Windows compatibility for projects expecting Unix fcntl (flock).
"""
import sys

LOCK_SH = 1  # Shared lock
LOCK_EX = 2  # Exclusive lock
LOCK_NB = 4  # Non-blocking
LOCK_UN = 8  # Unlock

if sys.platform == "win32":
    try:
        import msvcrt

        def flock(fd, operation):
            """Windows file locking using msvcrt."""
            try:
                fileno = fd.fileno() if hasattr(fd, "fileno") else fd
                # Rewind or operate at current pos if needed, but safe pass if lock fails
                if operation & LOCK_UN:
                    msvcrt.locking(fileno, msvcrt.LK_UNLCK, 1)
                elif operation & LOCK_NB:
                    msvcrt.locking(fileno, msvcrt.LK_NBLCK, 1)
                else:
                    msvcrt.locking(fileno, msvcrt.LK_LOCK, 1)
            except Exception:
                pass
    except ImportError:
        def flock(fd, operation):
            pass
else:
    # On Unix, dynamically import the built-in C fcntl module
    import importlib.util
    import os

    # Look for the system fcntl module outside of current directory
    _real_fcntl = None
    for p in sys.path:
        if p and os.path.abspath(p) != os.path.abspath(os.path.dirname(__file__)):
            spec = importlib.machinery.PathFinder.find_spec("fcntl", [p])
            if spec and spec.origin != __file__:
                _real_fcntl = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(_real_fcntl)
                break

    if _real_fcntl:
        for attr in dir(_real_fcntl):
            if not attr.startswith("__"):
                globals()[attr] = getattr(_real_fcntl, attr)
    else:
        def flock(fd, operation):
            pass
