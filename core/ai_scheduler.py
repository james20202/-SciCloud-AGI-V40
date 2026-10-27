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
        # DEPRECATED (top-5 honesty fix): the old ai_pipeline only
        # writes logs and never generates anything, yet returned True,
        # so callers marked episodes "完成". Never run it again and
        # never write a "完成" record from this path. Real production
        # goes through the workflow page (one-click production).
        # Kept as a guard instead of deleting the class, because
        # batch_engine and legacy pages still import it.
        self.status = "已废弃"
        logger.add(
            "已废弃：旧版 AI 调度不再执行，请到工作流页用一键出片生产"
        )
        return False

ai_scheduler=AIScheduler()

