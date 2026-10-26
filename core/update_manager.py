import os, re, shutil, subprocess, sys, tempfile, urllib.request, zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from core.config import BASE_DIR, BACKUP_DIR
from core.version import VERSION

# No manifest server is required. The online check reads the canonical
# version file from the main branch, and the one-click download uses the
# main-branch archive. Keeping MANIFEST_URL for backward compatibility
# only; check_online() no longer depends on it.
# Note: these unauthenticated URLs work only while the repository is
# publicly readable. If it is private, check_online() reports the failure
# clearly (it never claims "no update") and the ZIP-import fallback in
# System Center remains the working route.
MANIFEST_URL = ""
VERSION_URL = "https://raw.githubusercontent.com/james20202/-SciCloud-AGI-V40/main/core/version.py"
ARCHIVE_URL = "https://github.com/james20202/-SciCloud-AGI-V40/archive/refs/heads/main.zip"


def _version_tuple(version):
    """Parse '40.411.0' -> (40, 411, 0); non-numeric parts are ignored."""
    return tuple(int(p) for p in re.findall(r"\d+", str(version)))


def _compare_versions(local, latest):
    """Return 1 if latest > local, 0 if equal, -1 if latest < local."""
    a, b = _version_tuple(local), _version_tuple(latest)
    n = max(len(a), len(b))
    a = a + (0,) * (n - len(a))
    b = b + (0,) * (n - len(b))
    return (b > a) - (b < a)


def _parse_remote_version(text):
    m = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', text)
    return m.group(1).strip() if m else ""


class UpdateManager:
    def __init__(self):
        self.base = Path(BASE_DIR)
        self.backup = Path(BACKUP_DIR)

    def local_package(self, zip_path):
        return self._stage(zip_path)

    def download_and_stage(self, url=None):
        """Download a ZIP upgrade package and reuse the existing _stage()
        validation + runner launch. The downloaded file is removed after
        staging; the extracted stage directory is what the runner uses."""
        target_url = url or ARCHIVE_URL
        tmpdir = Path(tempfile.mkdtemp(prefix="scicloud_download_"))
        tmp_zip = tmpdir / "scicloud_upgrade.zip"
        try:
            req = urllib.request.Request(
                target_url, headers={"User-Agent": "SciCloud-AGI-V40"}
            )
            with urllib.request.urlopen(req, timeout=30) as r, open(tmp_zip, "wb") as f:
                while True:
                    chunk = r.read(1024 * 256)
                    if not chunk:
                        break
                    f.write(chunk)
            if not zipfile.is_zipfile(tmp_zip):
                raise ValueError("下载的文件不是有效的 ZIP 升级包")
            return self._stage(tmp_zip)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _stage(self, zip_path):
        z = Path(zip_path).expanduser().resolve()
        if not z.is_file() or z.suffix.lower() != '.zip':
            raise ValueError('请选择有效的 ZIP 升级包')
        stage = Path(tempfile.mkdtemp(prefix='scicloud_update_'))
        try:
            with zipfile.ZipFile(z, 'r') as archive:
                members = archive.infolist()
                if not members:
                    raise ValueError('升级包为空')
                for member in members:
                    name = member.filename.replace(chr(92), '/')
                    path = PurePosixPath(name)
                    mode = (member.external_attr >> 16) & 0o170000
                    if path.is_absolute() or '..' in path.parts or (path.parts and ':' in path.parts[0]):
                        raise ValueError(f'升级包包含不安全路径：{member.filename}')
                    if mode == 0o120000:
                        raise ValueError(f'升级包不允许包含符号链接：{member.filename}')
                archive.extractall(stage)
            roots = [p for p in stage.iterdir() if p.is_dir()]
            source = roots[0] if len(roots) == 1 and (roots[0] / 'main.py').is_file() else stage
            if not (source / 'main.py').is_file() or not (source / 'core').is_dir():
                raise ValueError('升级包结构不完整：必须包含 main.py 和 core/；未修改现有软件')
            return self._launch_runner(source)
        except Exception:
            shutil.rmtree(stage, ignore_errors=True)
            raise

    def _launch_runner(self, source):
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup = self.backup / f'update_{stamp}'
        backup.mkdir(parents=True, exist_ok=True)
        runner = self.base / 'apply_update.py'
        if not runner.is_file():
            raise FileNotFoundError(f'找不到升级执行器：{runner}')
        cmd = [sys.executable, str(runner), str(source), str(self.base), str(backup)]
        subprocess.Popen(cmd, cwd=str(self.base), start_new_session=True)
        return True

    def check_online(self):
        try:
            req = urllib.request.Request(
                VERSION_URL, headers={"User-Agent": "SciCloud-AGI-V40"}
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                text = r.read().decode('utf-8', errors='replace')
            latest = _parse_remote_version(text)
            if not latest:
                return {'available': False, 'version': VERSION, 'error': True,
                        'message': '检查失败：无法解析线上版本号；未确认是否有更新，请稍后重试或导入 ZIP 升级包。'}
            cmp = _compare_versions(VERSION, latest)
            if cmp > 0:
                return {'available': True, 'version': latest, 'url': ARCHIVE_URL,
                        'message': f'发现新版本 {latest}，当前版本 {VERSION}。'}
            if cmp < 0:
                # Local version is newer than main (e.g. a local dev build).
                return {'available': False, 'version': latest, 'url': ARCHIVE_URL,
                        'message': f'当前版本 {VERSION} 已高于线上版本 {latest}，无需升级。'}
            return {'available': False, 'version': latest, 'url': ARCHIVE_URL,
                    'message': f'已是最新版本（{VERSION}）。'}
        except Exception as e:
            # Never claim "no update" on a network failure.
            return {'available': False, 'version': VERSION, 'error': True,
                    'message': f'检查失败：{e}；未确认是否有更新，请稍后重试或导入 ZIP 升级包。'}

update_manager = UpdateManager()
