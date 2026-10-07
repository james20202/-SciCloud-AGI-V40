import os


class ImageGenerator:


    def create_task(
        self,
        scenes,
        output
    ):


        os.makedirs(
            output,
            exist_ok=True
        )


        files=[]


        for i,scene in enumerate(
            scenes,
            1
        ):


            filename = os.path.join(

                output,

                f"{i:03d}.txt"

            )


            with open(

                filename,

                "w",

                encoding="utf-8"

            ) as f:


                f.write(

                    scene

                )


            files.append(
                filename
            )


        return files



image_generator = ImageGenerator()

