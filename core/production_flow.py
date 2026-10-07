import json
import os
import time


class ProductionFlow:


    def __init__(self):

        self.status_file="production_flow.json"

        self.tasks={}

        self.load()



    def load(self):

        if os.path.exists(
            self.status_file
        ):

            with open(
                self.status_file,
                "r",
                encoding="utf-8"
            ) as f:

                self.tasks=json.load(f)



    def save(self):

        with open(
            self.status_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                self.tasks,
                f,
                ensure_ascii=False,
                indent=2
            )



    def create_task(
        self,
        project,
        episode
    ):


        key=project+"_"+episode


        self.tasks[key]={

            "剧本":"等待",

            "分镜":"等待",

            "素材":"等待",

            "视频":"等待"

        }


        self.save()



    def run(
        self,
        project,
        episode
    ):


        key=project+"_"+episode


        if key not in self.tasks:

            self.create_task(
                project,
                episode
            )


        steps=[

            "剧本",

            "分镜",

            "素材",

            "视频"

        ]


        for step in steps:


            self.tasks[key][step]="生产中"

            self.save()


            time.sleep(0.2)


            self.tasks[key][step]="完成"

            self.save()



        return True



    def get_status(self):

        return self.tasks



production_flow=ProductionFlow()

