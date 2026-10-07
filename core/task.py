

import time



class Task:


    def __init__(
        self,
        name
    ):

        self.name=name

        self.status="等待"



    def start(self):

        self.status="处理中"



    def finish(self):

        self.status="完成"



