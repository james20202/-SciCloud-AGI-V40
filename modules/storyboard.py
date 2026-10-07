

import os



def save_storyboard(project,episode,text):


    path=os.path.join(

        "projects",

        project,

        episode,

        "02_分镜"

    )


    os.makedirs(
        path,
        exist_ok=True
    )


    with open(

        os.path.join(path,"分镜.txt"),

        "w",

        encoding="utf-8"

    ) as f:


        f.write(text)





