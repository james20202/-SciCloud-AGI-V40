

import os


class ProjectManagerV5:


    def __init__(self):

        self.root="projects"



    def create(

        self,

        name,

        episode="001"

    ):


        base=os.path.join(

            self.root,

            name,

            "第"+episode+"集"

        )



        folders=[


            "01_剧本",

            "02_分镜",

            "03_图片素材",

            "04_动态视频",

            "05_配音",

            "06_字幕",

            "07_剪辑工程",

            "08_成片"


        ]



        for f in folders:


            os.makedirs(

                os.path.join(
                    base,
                    f
                ),

                exist_ok=True

            )


        return base



    def list(self):

        if not os.path.exists(
            self.root
        ):

            return []


        return os.listdir(
            self.root
        )

