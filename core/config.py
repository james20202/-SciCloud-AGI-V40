import os

APP_NAME = "SciCloud AGI V40"
VERSION = "40.404.0"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PROJECT_DIR = os.path.join(BASE_DIR, "projects")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
LOG_DIR = os.path.join(BASE_DIR, "logs")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

for path in [DATA_DIR, PROJECT_DIR, OUTPUT_DIR, LOG_DIR, BACKUP_DIR]:
    os.makedirs(path, exist_ok=True)
