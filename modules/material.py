

import os
import shutil



def save_image(src,project,episode):


    target = os.path.join(

        "projects",

        project,

        episode,

        "03_图片素材"

    )


    os.makedirs(
        target,
        exist_ok=True
    )


    shutil.copy(
        src,
        target
    )


    return target



