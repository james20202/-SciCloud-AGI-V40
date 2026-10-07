import os

from core.config import PROJECT_DIR
from core.database import (
    add_project,
    get_connection
)


EPISODE_FOLDERS = [

    "01_剧本",

    "02_分镜",

    "03_图片素材",

    "04_动态视频",

    "05_配音",

    "06_字幕",

    "07_剪辑工程",

    "08_成片"

]


def create_project(
    name,
    episode="001"
):

    # 创建数据库记录

    add_project(name)


    # 创建项目目录

    project_path = os.path.join(
        PROJECT_DIR,
        name
    )


    episode_path = os.path.join(
        project_path,
        "第"+episode+"集"
    )


    for folder in EPISODE_FOLDERS:

        os.makedirs(
            os.path.join(
                episode_path,
                folder
            ),
            exist_ok=True
        )


    # 添加章节数据

    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute(
    """
    SELECT id FROM projects
    WHERE name=?
    ORDER BY id DESC
    LIMIT 1
    """,
    (name,)
    )


    project_id = cursor.fetchone()[0]


    cursor.execute(
    """
    INSERT INTO episodes
    (
    project_id,
    episode
    )

    VALUES
    (?,?)
    """,
    (
    project_id,
    episode
    )
    )


    conn.commit()

    conn.close()


    return episode_path

