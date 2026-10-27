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
        # DEPRECATED (top-5 honesty fix): the old path ran the fake
        # ai_scheduler pipeline and then marked the episode "完成".
        # Never pop the queue, never call the scheduler, never mark
        # done from this path. Real batch production, if restored,
        # must run real one-click production per workflow (WF).
        return False

    def run_all(self):
        # DEPRECATED: see run_one. Do not loop: run_one() now always
        # returns False without consuming the queue, so a loop here
        # would never terminate.
        return False



    def get_status(self):

        return self.data



batch_engine=BatchEngine()

