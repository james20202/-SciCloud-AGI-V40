"""In-app preview for a finished episode video.

The user should not have to hunt through data folders to find the final
MP4. This dialog plays it inside SciCloud when QtMultimedia is available,
and always offers "open with the system player" as a fallback, plus the
exact file path so the result is never hidden behind a generic message.
"""
import os

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox,
)

try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PySide6.QtMultimediaWidgets import QVideoWidget
    HAS_MULTIMEDIA = True
except Exception:
    HAS_MULTIMEDIA = False


class VideoPreviewDialog(QDialog):
    def __init__(self, video_path, parent=None):
        super().__init__(parent)
        self.video_path = os.path.abspath(video_path)
        self.setWindowTitle("预览成片")
        self.resize(540, 980)
        root = QVBoxLayout(self)
        root.addWidget(QLabel(f"成片：{self.video_path}"))
        self.player = None
        if HAS_MULTIMEDIA:
            self.video_widget = QVideoWidget()
            root.addWidget(self.video_widget, 1)
            self.player = QMediaPlayer(self)
            self.audio_output = QAudioOutput(self)
            self.player.setAudioOutput(self.audio_output)
            self.player.setVideoOutput(self.video_widget)
            self.player.setSource(QUrl.fromLocalFile(self.video_path))
            self.play_button = QPushButton("▶ 播放")
            self.play_button.clicked.connect(self._toggle_play)
            root.addWidget(self.play_button)
        else:
            root.addWidget(QLabel("本机 QtMultimedia 不可用，无法在应用内播放，请用系统播放器打开。"))
        bar = QHBoxLayout()
        open_button = QPushButton("用系统播放器打开")
        open_button.clicked.connect(self._open_externally)
        bar.addWidget(open_button)
        copy_button = QPushButton("复制成片路径")
        copy_button.clicked.connect(self._copy_path)
        bar.addWidget(copy_button)
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.close)
        bar.addWidget(close_button)
        root.addLayout(bar)

    def _toggle_play(self):
        if not self.player:
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.play_button.setText("▶ 播放")
        else:
            self.player.play()
            self.play_button.setText("⏸ 暂停")

    def _open_externally(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.video_path))

    def _copy_path(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.video_path)
        QMessageBox.information(self, "已复制", "成片路径已复制到剪贴板。")

    def closeEvent(self, event):
        if self.player:
            self.player.stop()
        super().closeEvent(event)
