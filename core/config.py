import os

APP_NAME = "SciCloud AGI V40"
VERSION = "40.301.0"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Prefer user-configured external storage on macOS and fallback to repo-local dirs.
DATA_DIR = os.environ.get("SCI_DATA_DIR", os.path.join("/Volumes/修仙漫剧/SciCloud AGI V40", "data"))
PROJECT_DIR = os.environ.get("SCI_PROJECT_DIR", os.path.join("/Volumes/修仙漫剧/SciCloud AGI V40", "projects"))
OUTPUT_DIR = os.environ.get("SCI_OUTPUT_DIR", os.path.join("/Volumes/修仙漫剧/SciCloud AGI V40", "output"))
LOG_DIR = os.environ.get("SCI_LOG_DIR", os.path.join("/Volumes/修仙漫剧/SciCloud AGI V40", "logs"))
BACKUP_DIR = os.environ.get("SCI_BACKUP_DIR", os.path.join("/Volumes/修仙漫剧/SciCloud AGI V40", "backups"))

for path in [DATA_DIR, PROJECT_DIR, OUTPUT_DIR, LOG_DIR, BACKUP_DIR]:
    os.makedirs(path, exist_ok=True)
