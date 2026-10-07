import os
import json



class ProjectContext:


    def __init__(self):

        self.project=""

        self.episode=""

        self.root=""



    def set_project(
        self,
        project,
        episode
    ):

        self.project = project

        self.episode = episode


        self.root=os.path.join(

            "projects",

            project,

            "第"+episode+"集"

        )



    def get_root(self):

        return self.root



    def get_script_path(self):

        return os.path.join(

            self.root,

            "01_剧本",

            "剧本.txt"

        )



    def load_script(self):


        path=self.get_script_path()


        if not os.path.exists(path):

            return ""


        with open(

            path,

            "r",

            encoding="utf-8"

        ) as f:

            return f.read()



    def get_character_path(self):


        return os.path.join(

            "projects",

            self.project,

            "角色库",

            "角色.json"

        )



    def load_characters(self):


        path=self.get_character_path()


        if not os.path.exists(path):

            return {}



        with open(

            path,

            "r",

            encoding="utf-8"

        ) as f:


            return json.load(f)




context=ProjectContext()

