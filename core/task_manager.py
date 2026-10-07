class TaskManager:


    def __init__(self):

        self.tasks = {

            "剧本":"未开始",

            "分镜":"未开始",

            "图片素材":"未开始",

            "视频":"未开始"

        }



    def update(
        self,
        name,
        status
    ):

        if name in self.tasks:

            self.tasks[name] = status



    def status(
        self,
        name
    ):

        return self.tasks.get(

            name,

            "未开始"

        )



    def get_tasks(self):


        result=[]


        for k,v in self.tasks.items():

            result.append(

                {

                    "name":k,

                    "status":v

                }

            )


        return result



    def progress(self):


        total=len(
            self.tasks
        )


        done=0


        for value in self.tasks.values():


            if value=="完成":

                done+=1



        if total==0:

            return 0



        return int(

            done/total*100

        )



tasks = TaskManager()

