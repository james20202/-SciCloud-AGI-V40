import json, os, shutil, subprocess, sys, tempfile, urllib.request, zipfile
from datetime import datetime
from pathlib import Path
from core.config import BASE_DIR, BACKUP_DIR
from core.version import VERSION

MANIFEST_URL = ""  # Future GitHub Releases manifest URL can be placed here.

class UpdateManager:
    def __init__(self):
        self.base = Path(BASE_DIR)
        self.backup = Path(BACKUP_DIR)

    def local_package(self, zip_path):
        return self._stage(zip_path)

    def _stage(self, zip_path):
        z = Path(zip_path).expanduser().resolve()
        if not z.exists() or z.suffix.lower() != '.zip':
            raise ValueError('请选择有效的 ZIP 升级包')
        stage = Path(tempfile.mkdtemp(prefix='scicloud_update_'))
        with zipfile.ZipFile(z, 'r') as f:
            f.extractall(stage)
        roots = [p for p in stage.iterdir() if p.is_dir()]
        source = roots[0] if len(roots) == 1 and (roots[0]/'main.py').exists() else stage
        return self._launch_runner(source)

    def _launch_runner(self, source):
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup = self.backup / f'update_{stamp}'
        backup.mkdir(parents=True, exist_ok=True)
        runner = self.base / 'apply_update.py'
        cmd = [sys.executable, str(runner), str(source), str(self.base), str(backup)]
        subprocess.Popen(cmd, cwd=str(self.base), start_new_session=True)
        return True

    def check_online(self):
        if not MANIFEST_URL:
            return {'available': False, 'version': VERSION, 'message': '在线升级通道尚未配置；可直接导入 ZIP 升级包。'}
        try:
            with urllib.request.urlopen(MANIFEST_URL, timeout=5) as r:
                data = json.loads(r.read().decode('utf-8'))
            latest = str(data.get('version',''))
            return {'available': latest and latest != VERSION, 'version': latest, 'url': data.get('url',''), 'message': data.get('notes','')}
        except Exception as e:
            return {'available': False, 'version': VERSION, 'message': f'检查失败：{e}'}

update_manager = UpdateManager()
