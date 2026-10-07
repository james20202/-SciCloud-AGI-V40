

import os
from datetime import datetime



LOG_DIR="logs"

os.makedirs(
    LOG_DIR,
    exist_ok=True
)



LOG_FILE=os.path.join(
    LOG_DIR,
    "system.log"
)



def log(message):


    time=datetime.now().strftime(

        "%Y-%m-%d %H:%M:%S"

    )


    text=f"[{time}] {message}\n"


    with open(
        LOG_FILE,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(text)



    return text

