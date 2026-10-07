

import os


CURRENT_PROJECT = ""
CURRENT_EPISODE = ""



def set_project(name):

    global CURRENT_PROJECT

    CURRENT_PROJECT = name



def set_episode(ep):

    global CURRENT_EPISODE

    CURRENT_EPISODE = ep



def get_current():

    return {

        "project":CURRENT_PROJECT,

        "episode":CURRENT_EPISODE

    }



def project_path():

    return os.path.join(

        "projects",

        CURRENT_PROJECT,

        CURRENT_EPISODE

    )

