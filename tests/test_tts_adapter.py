import os
import sys

from core.adapters.tts_adapter import TTSCommandAdapter


def test_tts_adapter_returns_only_verified_nonempty_audio_output(tmp_path):
    output = tmp_path / "voice.wav"
    command = [
        sys.executable,
        "-c",
        "import pathlib,sys; pathlib.Path(sys.argv[1]).write_bytes(b'audio')",
        "{output}",
    ]

    result = TTSCommandAdapter().execute(
        {"command": ""},
        {"command": command, "output_path": str(output)},
        {},
    )

    assert result.success is True
    assert result.outputs == [str(output.resolve())]
    assert output.read_bytes() == b"audio"
    assert result.data["size_bytes"] == 5


def test_tts_adapter_rejects_successful_command_without_audio_file(tmp_path):
    output = tmp_path / "missing.wav"
    command = [sys.executable, "-c", "pass", "{output}"]

    result = TTSCommandAdapter().execute(
        {},
        {"command": command, "output_path": str(output)},
        {},
    )

    assert result.success is False
    assert "不存在或为空" in result.message
    assert result.outputs == []


def test_tts_adapter_requires_explicit_output_path():
    result = TTSCommandAdapter().execute(
        {"command": sys.executable},
        {},
        {},
    )

    assert result.success is False
    assert "缺少 output_path/output_file" in result.message


def test_tts_adapter_rejects_missing_executable(tmp_path):
    result = TTSCommandAdapter().execute(
        {},
        {"command": ["scicloud-command-that-does-not-exist"], "output_path": str(tmp_path / "voice.wav")},
        {},
    )

    assert result.success is False
    assert "找不到 TTS 可执行文件" in result.message

def test_tts_adapter_binds_story_text_and_output_placeholders(tmp_path):
    output = tmp_path / "narration.wav"
    command = [
        sys.executable,
        "-c",
        "import pathlib,sys; pathlib.Path(sys.argv[1]).write_bytes(sys.argv[2].encode())",
        "{output}",
        "{text}",
    ]

    result = TTSCommandAdapter().execute(
        {},
        {"command": command, "output_path": str(output), "text": "主角：剑来！"},
        {},
    )

    assert result.success is True
    assert output.read_text(encoding="utf-8") == "主角：剑来！"


def test_tts_adapter_rejects_text_when_command_has_no_text_placeholder(tmp_path):
    output = tmp_path / "narration.wav"
    command = [
        sys.executable,
        "-c",
        "import pathlib,sys; pathlib.Path(sys.argv[-1]).write_bytes(b'audio')",
    ]

    result = TTSCommandAdapter().execute(
        {},
        {"command": command, "output_path": str(output), "text": "需要朗读的内容"},
        {},
    )

    assert result.success is False
    assert "{text}" in result.message

