class StoryAI:


    def analyze(
        self,
        text
    ):


        result = {

            "title":
            "自动分析剧情",

            "summary":
            text[:100],

            "characters":
            [],

            "scenes":
            []

        }


        return result



story_ai = StoryAI()

