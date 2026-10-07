
import json
import os
import time


class PipelineManager:


    def __init__(self):

        self.file="data/v30/pipeline.json"

        self.tasks={}

        self.load()



    def load(self):

        if os.path.exists(self.file):

            with open(
                self.file,
                "r",
                encoding="utf-8"
            ) as f:

                self.tasks=json.load(f)



    def save(self):

        os.makedirs(
            "data/v30",
            exist_ok=True
        )


        with open(
            self.file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                self.tasks,
                f,
                ensure_ascii=False,
                indent=2
            )



    def create(
        self,
        project,
        episode
    ):


        key=f"{project}_{episode}"


        self.tasks[key]={

            "剧本":"等待",

            "角色":"等待",

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


        key=f"{project}_{episode}"


        if key not in self.tasks:

            self.create(
                project,
                episode
            )


        for step in self.tasks[key]:

            self.tasks[key][step]="生产中"

            self.save()


            time.sleep(0.2)


            self.tasks[key][step]="完成"

            self.save()



        return True


    def get_status(self):
        return self.tasks


pipeline_manager=PipelineManager()

