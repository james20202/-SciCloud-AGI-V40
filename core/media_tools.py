"""Find local media tools even when a Finder-launched app has a minimal PATH.

On macOS, a packaged app launched from Finder does not inherit a shell PATH,
so /opt/homebrew/bin/ffmpeg and ffprobe are invisible to shutil.which even
though Homebrew installed them. This helper searches PATH first, then the
usual Homebrew / local locations, and returns an absolute path or None.
It never downloads anything and never changes PATH globally.
"""
import os
import shutil

_EXTRA_DIRS = ("/opt/homebrew/bin", "/usr/local/bin", "/opt/homebrew/sbin", "/usr/local/sbin")


def find_tool(name):
    found = shutil.which(name)
    if found:
        return found
    if os.path.sep in name:
        return name if (os.path.isfile(name) and os.access(name, os.X_OK)) else None
    for directory in _EXTRA_DIRS:
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None
