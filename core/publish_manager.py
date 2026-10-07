import os
import json



class PublishManager:


    def __init__(self):

        self.file="publish.json"

        self.data={}

        self.load()



    def load(self):


        if os.path.exists(
            self.file
        ):


            with open(

                self.file,

                "r",

                encoding="utf-8"

            ) as f:


                self.data=json.load(f)



    def save(self):


        with open(

            self.file,

            "w",

            encoding="utf-8"

        ) as f:


            json.dump(

                self.data,

                f,

                ensure_ascii=False,

                indent=2

            )



    def create(
        self,
        episode
    ):


        self.data[episode]={

            "video":"完成",

            "subtitle":"待检查",

            "cover":"待制作",

            "status":"待发布"

        }


        self.save()



    def update(
        self,
        episode,
        key,
        value
    ):


        if episode not in self.data:

            self.create(
                episode
            )


        self.data[episode][key]=value


        self.save()



    def get_all(self):


        return self.data




publish_manager=PublishManager()

