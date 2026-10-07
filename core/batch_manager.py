from core.project_context import context

from core.ai_pipeline import ai_pipeline

from core.logger_center import logger

from core.production_record import record



class BatchManager:


    def __init__(self):

        self.queue=[]

        self.current=None



    def create_queue(
        self,
        project,
        start,
        end
    ):


        self.queue=[]


        for i in range(
            start,
            end+1
        ):


            ep=str(i).zfill(3)


            status=record.get_status(
                ep
            )


            if status=="完成":

                continue



            self.queue.append(

                {

                    "project":project,

                    "episode":ep,

                    "status":status

                }

            )



    def run_next(self):


        if not self.queue:


            logger.add(
                "没有待生产任务"
            )


            return False



        task=self.queue.pop(0)


        self.current=task



        ep=task["episode"]



        logger.add(

            "开始制作第"

            +

            ep

            +

            "集"

        )



        context.set_project(

            task["project"],

            ep

        )



        record.set_status(

            ep,

            "生产中"

        )



        result=ai_pipeline.run()



        if result:


            record.set_status(

                ep,

                "完成"

            )


            logger.add(

                "第"

                +

                ep

                +

                "集完成"

            )



        else:


            record.set_status(

                ep,

                "失败"

            )


            logger.add(

                "第"

                +

                ep

                +

                "集失败"

            )



        return True




batch_manager=BatchManager()

