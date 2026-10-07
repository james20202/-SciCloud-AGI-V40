import os


from core.data_center import app_data

from core.task_manager import tasks

from core.ai.story_ai import story_ai

from core.ai.storyboard_ai import storyboard_ai

from core.generator.image_generator import image_generator

from core.generator.video_generator import video_generator

from core.logger_center import logger



class ProductionEngine:


    def __init__(self):

        self.running = False

        self.message = "等待"



    def start(self):


        if self.running:

            return


        self.running = True


        try:


            logger.add(
                "开始制作第001集"
            )


            # 剧本

            tasks.update(
                "剧本",
                "进行中"
            )

            logger.add(
                "读取剧本"
            )


            script = self.load_script()


            story = story_ai.analyze(
                script
            )


            tasks.update(
                "剧本",
                "完成"
            )


            logger.add(
                "剧本分析完成"
            )



            # 分镜

            tasks.update(
                "分镜",
                "进行中"
            )


            logger.add(
                "生成分镜"
            )


            scenes = storyboard_ai.generate(
                story
            )


            tasks.update(
                "分镜",
                "完成"
            )


            logger.add(
                "分镜生成完成"
            )



            # 图片

            tasks.update(
                "图片素材",
                "进行中"
            )


            logger.add(
                "创建图片任务"
            )


            descriptions=[]


            for scene in scenes:

                descriptions.append(
                    scene["description"]
                )



            root = app_data.get_root()


            image_dir=os.path.join(

                root,

                "03_图片素材"

            )


            images=image_generator.create_task(

                descriptions,

                image_dir

            )


            tasks.update(
                "图片素材",
                "完成"
            )


            logger.add(
                "图片任务完成"
            )



            # 视频

            tasks.update(
                "视频",
                "进行中"
            )


            logger.add(
                "开始视频生成"
            )


            video_dir=os.path.join(

                root,

                "05_视频"

            )


            video_generator.create(

                images,

                video_dir

            )


            tasks.update(
                "视频",
                "完成"
            )


            logger.add(
                "视频生成完成"
            )


            self.message="制作完成"


            logger.add(
                "第001集制作完成"
            )



        except Exception as e:


            self.message=str(e)

            logger.add(
                "错误："+str(e)
            )



        finally:

            self.running=False



    def load_script(self):


        path = app_data.get_script_file()


        if not path or not os.path.exists(path):

            return "暂无剧本"



        with open(

            path,

            "r",

            encoding="utf-8"

        ) as f:


            return f.read()



production = ProductionEngine()

