from datetime import datetime


class LoggerCenter:


    def __init__(self):

        self.logs=[]



    def add(self,text):

        msg = (

            datetime.now().strftime(
                "%H:%M:%S"
            )

            +

            " "

            +

            text

        )

        self.logs.append(
            msg
        )



    def get(self):

        return "\n".join(
            self.logs
        )



logger = LoggerCenter()

