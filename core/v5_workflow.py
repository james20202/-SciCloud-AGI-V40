

class WorkflowV5:


    stages=[

        "剧本",

        "分镜",

        "素材",

        "配音",

        "字幕",

        "视频",

        "完成"

    ]



    def get_status(self):


        return {

            x:"等待"

            for x in self.stages

        }



    def update(

        self,

        stage,

        value

    ):


        return {

            stage:value

        }

