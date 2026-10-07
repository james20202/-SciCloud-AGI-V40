from core.logger_center import logger

from core.project_context import context



class AIPipeline:


    def __init__(self):

        self.status="等待"

        self.characters={}



    def run(
        self,
        script=None
    ):


        try:


            logger.add(
                "AI生产链启动"
            )



            if not script:


                script=context.load_script()



            if not script:


                logger.add(
                    "未找到剧本"
                )


                self.status="错误"


                return False



            logger.add(
                "剧本读取完成"
            )



            self.characters = context.load_characters()



            if self.characters:


                logger.add(
                    "角色库加载完成"
                )

            else:

                logger.add(
                    "未检测到角色库"
                )



            self.status="分析剧情"



            logger.add(
                "AI分析剧情"
            )



            self.status="角色绑定"



            logger.add(
                "绑定角色设定"
            )



            self.status="生成分镜"



            logger.add(
                "生成带角色分镜"
            )



            self.status="生成素材"



            logger.add(
                "生成素材任务"
            )



            self.status="完成"



            logger.add(
                "AI生产链完成"
            )


            return True



        except Exception as e:


            logger.add(
                "错误："+str(e)
            )


            self.status="错误"


            return False




ai_pipeline=AIPipeline()

