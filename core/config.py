import os
import sys

APP_NAME = "SciCloud AGI V40"
VERSION = "40.412.0"


def _resolve_base_dir():
    """Return the directory that holds user data (data/, projects/, ...).

    Source runs (python main.py / launch.command) keep the historical
    behaviour: the repository/install directory that contains core/.

    Packaged runs (PyInstaller, sys.frozen) must NOT resolve user data
    inside the .app bundle: under PyInstaller, __file__ points into
    Contents/MacOS/_internal, so the old dirname(dirname(__file__))
    rule would lock projects/data/output inside the bundle, and moving
    the .app would silently orphan the user's data. Instead:

    - SCICLOUD_HOME, when set, wins: point it at the old install
      directory to keep using the existing projects/data/output, e.g.
      SCICLOUD_HOME="/Volumes/修仙漫剧/SciCloud AGI V40".
    - Otherwise a frozen build uses ~/SciCloud AGI V40, a stable
      directory outside the bundle that survives moving the .app.
    """
    env_home = os.environ.get("SCICLOUD_HOME")
    if env_home:
        return os.path.abspath(os.path.expanduser(env_home))
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.expanduser("~"), "SciCloud AGI V40")
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


BASE_DIR = _resolve_base_dir()
DATA_DIR = os.path.join(BASE_DIR, "data")
PROJECT_DIR = os.path.join(BASE_DIR, "projects")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
LOG_DIR = os.path.join(BASE_DIR, "logs")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

for path in [DATA_DIR, PROJECT_DIR, OUTPUT_DIR, LOG_DIR, BACKUP_DIR]:
    os.makedirs(path, exist_ok=True)
