

import os
import json
from datetime import datetime


FILE="data/app_state.json"



class DataCenter:


    def __init__(self):

        self.project=None

        self.episode="001"

        self.status="空闲"

        self.load()



    def set_project(
        self,
        project,
        episode="001"
    ):

        self.project=project

        self.episode=episode

        self.status="项目切换"

        self.save()



    def get_project(self):

        return self.project



    def get_episode(self):

        return self.episode



    def get_root(self):

        if not self.project:

            return None


        return os.path.join(

            "projects",

            self.project,

            "第"+self.episode+"集"

        )



    def get_script_file(self):

        root=self.get_root()


        if not root:

            return None


        path=os.path.join(

            root,

            "01_剧本"

        )


        os.makedirs(

            path,

            exist_ok=True

        )


        return os.path.join(

            path,

            "剧本.txt"

        )



    def save(self):

        os.makedirs(

            "data",

            exist_ok=True

        )


        with open(

            FILE,

            "w",

            encoding="utf-8"

        ) as f:


            json.dump(

                {

                    "project":self.project,

                    "episode":self.episode,

                    "status":self.status,

                    "update":

                    datetime.now().strftime(

                        "%Y-%m-%d %H:%M:%S"

                    )

                },

                f,

                ensure_ascii=False,

                indent=2

            )



    def load(self):

        if os.path.exists(FILE):

            with open(

                FILE,

                "r",

                encoding="utf-8"

            ) as f:


                data=json.load(f)


                self.project=data.get(
                    "project"
                )

                self.episode=data.get(
                    "episode",
                    "001"
                )

                self.status=data.get(
                    "status",
                    "空闲"
                )



app_data=DataCenter()

