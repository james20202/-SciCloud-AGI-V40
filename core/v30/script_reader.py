
import os


class ScriptReader:


    def read(self, path):

        if not os.path.exists(path):

            return ""


        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return f.read()



    def analyze(self, text):

        return {

            "length":len(text),

            "scenes":text.count("场"),

            "characters":text.count("：")

        }



script_reader=ScriptReader()

