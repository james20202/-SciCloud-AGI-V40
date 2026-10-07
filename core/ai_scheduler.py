from core.logger_center import logger

from core.ai_pipeline import ai_pipeline

from core.project_context import context

from core.production_record import record



class AIScheduler:


    def __init__(self):

        self.status="等待"

        self.tasks=[]

        self.current=None



    def create_task(
        self,
        project,
        episode
    ):


        self.tasks.append(

            {

                "project":project,

                "episode":str(episode).zfill(3),

                "status":"等待"

            }

        )


        logger.add(

            "创建AI任务："

            +

            project

            +

            " 第"

            +

            str(episode)

            +

            "集"

        )



    def run(self):


        if not self.tasks:


            logger.add(
                "没有AI任务"
            )

            return False



        self.current=self.tasks.pop(0)


        project=self.current["project"]

        episode=self.current["episode"]



        context.set_project(

            project,

            episode

        )



        try:


            self.status="AI分析"


            logger.add(

                "AI开始分析第"

                +

                episode

                +

                "集"

            )



            record.set_status(

                episode,

                "AI生产中"

            )



            result=ai_pipeline.run()



            if result:


                record.set_status(

                    episode,

                    "完成"

                )


                self.status="完成"


                logger.add(

                    "AI任务完成 第"

                    +

                    episode

                    +

                    "集"

                )


            else:


                record.set_status(

                    episode,

                    "失败"

                )


                self.status="失败"



            return result



        except Exception as e:


            self.status="错误"


            logger.add(

                "AI调度错误："

                +

                str(e)

            )


            return False




ai_scheduler=AIScheduler()

