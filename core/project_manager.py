import os
import json



class ProjectManager:


    def __init__(self):

        self.root = "projects"

        self.file = "projects.json"

        self.projects = {}

        self.load()



    def load(self):


        if os.path.exists(
            self.file
        ):


            with open(

                self.file,

                "r",

                encoding="utf-8"

            ) as f:


                self.projects = json.load(f)



    def save(self):


        with open(

            self.file,

            "w",

            encoding="utf-8"

        ) as f:


            json.dump(

                self.projects,

                f,

                ensure_ascii=False,

                indent=2

            )



    def create_project(
        self,
        name
    ):


        if name not in self.projects:


            self.projects[name]={

                "status":"等待",

                "episodes":[]

            }


            path=os.path.join(

                self.root,

                name

            )


            os.makedirs(

                path,

                exist_ok=True

            )


            self.save()



    def add_episode(
        self,
        project,
        episode
    ):


        if project not in self.projects:

            self.create_project(
                project
            )



        ep=str(episode).zfill(3)



        if ep not in self.projects[project]["episodes"]:


            self.projects[project]["episodes"].append(

                ep

            )


        self.save()



    def set_status(
        self,
        project,
        status
    ):


        if project in self.projects:


            self.projects[project]["status"]=status


            self.save()



    def get_projects(self):


        return self.projects



    def get_project_count(self):


        return len(
            self.projects
        )




project_manager=ProjectManager()

