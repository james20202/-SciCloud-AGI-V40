import sqlite3
import os

from core.config import DATA_DIR


DB_PATH = os.path.join(
    DATA_DIR,
    "xianju.db"
)


def get_connection():

    return sqlite3.connect(
        DB_PATH
    )


def init_database():

    conn = get_connection()

    cursor = conn.cursor()


    # 作品表

    cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS projects
    (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT NOT NULL,

        created_time TEXT,

        status TEXT
    )
    """
    )


    # 章节表

    cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS episodes
    (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        project_id INTEGER,

        episode TEXT,

        image_count INTEGER DEFAULT 0,

        audio_status TEXT DEFAULT '未上传',

        video_status TEXT DEFAULT '未生成'
    )
    """
    )


    conn.commit()

    conn.close()



def add_project(name):

    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute(
    """
    INSERT INTO projects
    (name, created_time, status)

    VALUES
    (?, datetime('now'), ?)
    """,
    (
        name,
        "创建"
    )
    )


    conn.commit()

    conn.close()



def get_projects():

    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute(
    """
    SELECT * FROM projects
    """
    )


    data = cursor.fetchall()


    conn.close()


    return data

