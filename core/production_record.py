import os
import json



class ProductionRecord:


    def __init__(self):

        self.file="production.json"

        self.data={}



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



    def set_status(
        self,
        episode,
        status
    ):


        self.data[episode]=status

        self.save()



    def get_status(
        self,
        episode
    ):


        return self.data.get(

            episode,

            "未开始"

        )




record=ProductionRecord()

record.load()

