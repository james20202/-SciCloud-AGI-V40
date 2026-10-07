import time
import threading

from core.task_manager import tasks


STEPS = [
    "剧本",
    "分镜",
    "图片素材",
    "配音",
    "视频"
]


class Pipeline:


    def __init__(self):

        self.running = False
        self.current = "空闲"



    def start(self, callback=None):

        if self.running:
            return


        thread = threading.Thread(
            target=self.run,
            args=(callback,)
        )

        thread.start()



    def run(self, callback=None):

        self.running = True


        for step in STEPS:


            self.current = step


            tasks.update(
                step,
                "进行中"
            )


            if callback:

                callback(
                    step,
                    "进行中"
                )


            time.sleep(2)



            tasks.update(
                step,
                "完成"
            )


            if callback:

                callback(
                    step,
                    "完成"
                )


        self.current = "完成"

        self.running = False



pipeline = Pipeline()

