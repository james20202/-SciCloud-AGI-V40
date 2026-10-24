import os
import tempfile
import unittest
from types import SimpleNamespace

from core.local_tts_engine import LocalTTSEngine, sanitize_dialogue_for_prompt, strip_non_dialogue_brackets


class LocalTTSEngineTests(unittest.TestCase):
    def test_removes_stage_directions_but_preserves_spoken_words(self):
        self.assertEqual(strip_non_dialogue_brackets("（低声）天命已至！"), "天命已至！")
        self.assertEqual(strip_non_dialogue_brackets("(只有风声)"), "")

    def test_prompt_does_not_include_actual_dialogue(self):
        prompt = sanitize_dialogue_for_prompt("你竟敢欺骗我！", "林青")
        self.assertIn("林青", prompt)
        self.assertIn("speaking", prompt)
        self.assertNotIn("欺骗", prompt)

    def test_local_say_output_must_be_a_real_nonempty_file(self):
        with tempfile.TemporaryDirectory() as root:
            out = os.path.join(root, "voice.aiff")
            def fake_run(command, **kwargs):
                output = command[command.index("-o") + 1]
                with open(output, "wb") as stream:
                    stream.write(b"audio")
                return SimpleNamespace(returncode=0, stderr="", stdout="")
            engine = LocalTTSEngine(environ={"SCICLOUD_TTS_BACKEND": "say"}, which=lambda name: "/usr/bin/say" if name == "say" else None, run=fake_run)
            result = engine.synthesize("你好", out)
            self.assertTrue(result["success"])
            self.assertEqual(result["backend"], "say")
            self.assertGreater(result["size_bytes"], 0)

    def test_missing_local_tts_does_not_claim_success(self):
        engine = LocalTTSEngine(environ={"SCICLOUD_TTS_BACKEND": "auto"}, which=lambda name: None)
        result = engine.synthesize("你好", "/tmp/should-not-be-created.aiff")
        self.assertFalse(result["success"])
        self.assertIn("未发现", result["message"])


if __name__ == "__main__":
    unittest.main()
