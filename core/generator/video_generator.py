import os
from datetime import datetime



class VideoGenerator:


    def create(

        self,

        images,

        output

    ):


        os.makedirs(

            output,

            exist_ok=True

        )


        file=os.path.join(

            output,

            "第001集_预览视频.txt"

        )


        with open(

            file,

            "w",

            encoding="utf-8"

        ) as f:


            f.write(

                "视频生成任务\n"

                +

                "图片数量："

                +

                str(len(images))

                +

                "\n时间："

                +

                datetime.now().strftime(

                    "%Y-%m-%d %H:%M:%S"

                )

            )


        return file



video_generator = VideoGenerator()

