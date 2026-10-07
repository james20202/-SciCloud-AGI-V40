import json
import os

from core.ai_scheduler import ai_scheduler


class BatchEngine:


    def __init__(self):

        self.queue=[]

        self.status_file="batch_status.json"

        self.load()



    def load(self):

        if os.path.exists(self.status_file):

            with open(
                self.status_file,
                "r",
                encoding="utf-8"
            ) as f:

                self.data=json.load(f)

        else:

            self.data={}



    def save(self):

        with open(
            self.status_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                self.data,
                f,
                ensure_ascii=False,
                indent=2
            )



    def create_batch(
        self,
        project,
        start,
        end
    ):

        self.queue=[]


        if project not in self.data:

            self.data[project]={}



        for i in range(
            int(start),
            int(end)+1
        ):

            ep=str(i).zfill(3)

            self.queue.append({

                "project":project,

                "episode":ep,

                "status":"等待"

            })


            self.data[project][ep]="等待"



        self.save()

        return self.queue



    def run_one(self):


        if not self.queue:

            return False



        task=self.queue.pop(0)


        task["status"]="生产中"


        project=task["project"]

        ep=task["episode"]


        self.data[project][ep]="生产中"

        self.save()



        ai_scheduler.create_task(
            project,
            ep
        )


        result=ai_scheduler.run()



        if result:

            self.data[project][ep]="完成"

        else:

            self.data[project][ep]="失败"



        self.save()


        return True



    def run_all(self):


        while self.queue:

            self.run_one()



        return True



    def get_status(self):

        return self.data



batch_engine=BatchEngine()

