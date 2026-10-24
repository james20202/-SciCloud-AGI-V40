from pathlib import Path
import zipfile
import pytest
from core.update_manager import UpdateManager


def test_rejects_unrelated_zip(tmp_path, monkeypatch):
    package = tmp_path / 'wrong.zip'
    with zipfile.ZipFile(package, 'w') as z:
        z.writestr('notes.txt', 'not an update')
    manager = UpdateManager()
    launched = []
    monkeypatch.setattr(manager, '_launch_runner', lambda source: launched.append(source) or True)
    with pytest.raises(ValueError, match='结构不完整'):
        manager._stage(package)
    assert launched == []


def test_accepts_flat_upgrade_zip(tmp_path, monkeypatch):
    package = tmp_path / 'valid.zip'
    with zipfile.ZipFile(package, 'w') as z:
        z.writestr('main.py', 'print(1)')
        z.writestr('core/__init__.py', '')
    manager = UpdateManager()
    launched = []
    monkeypatch.setattr(manager, '_launch_runner', lambda source: launched.append(source) or True)
    assert manager._stage(package) is True
    assert len(launched) == 1
    assert (Path(launched[0]) / 'main.py').is_file()
