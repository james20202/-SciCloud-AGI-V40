import json
import os


FILE = "data/workflow.json"



DEFAULT = {

    "剧本": "未完成",
    "分镜": "未完成",
    "素材": "未完成",
    "配音": "未完成",
    "视频": "未完成"

}



class Workflow:


    def __init__(self):

        self.data = DEFAULT.copy()

        self.load()



    def update(
        self,
        name,
        status
    ):

        self.data[name] = status

        self.save()



    def load(self):

        if os.path.exists(FILE):

            with open(
                FILE,
                "r",
                encoding="utf-8"
            ) as f:

                self.data = json.load(f)



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
                self.data,
                f,
                ensure_ascii=False,
                indent=2
            )



workflow = Workflow()

