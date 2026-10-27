"""List real V40 publish packages for PublishCenter.

The old PublishCenter read a legacy publish.json that is never
written by the V40 production chain, so its list was always empty
while the real packages sat elsewhere. Real V40 packages are:

- Workflow TASK-12 (execution_engine publish task):
  <PROJECT_DIR>/output/packages/<workflow_id>_episode_package.zip
- EP route (publish_pack_engine.build):
  <OUTPUT_DIR>/<episode_id>_publish.zip

This module only lists those files. It never writes a "published"
state: a local zip is a deliverable, not proof of upload.
"""
import os
import zipfile
from datetime import datetime


def _default_dirs():
    from core.config import PROJECT_DIR, OUTPUT_DIR

    return (
        os.path.join(PROJECT_DIR, "output", "packages"),
        OUTPUT_DIR,
    )


def list_real_packages(packages_dir=None, ep_output_dir=None):
    """Return real package zips, newest first.

    Each entry: {name, path, size_bytes, modified}.
    Directories may be overridden for tests; defaults come from
    core.config (resolved lazily so importing this module never
    creates directories as a side effect).
    """
    if packages_dir is None or ep_output_dir is None:
        default_packages, default_output = _default_dirs()
        packages_dir = packages_dir if packages_dir is not None else default_packages
        ep_output_dir = ep_output_dir if ep_output_dir is not None else default_output
    found = []
    for directory, suffix in ((packages_dir, "_episode_package.zip"), (ep_output_dir, "_publish.zip")):
        if not directory or not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory)):
            if not name.endswith(suffix):
                continue
            path = os.path.join(directory, name)
            if not os.path.isfile(path):
                continue
            try:
                size = os.path.getsize(path)
                modified = datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds")
            except OSError:
                continue
            found.append({"name": name, "path": path, "size_bytes": size, "modified": modified})
    found.sort(key=lambda item: item["modified"], reverse=True)
    return found


def package_contents(path):
    """Read-only zip listing for the check view. Returns [] when the
    file cannot be read as a zip instead of raising into the UI."""
    try:
        with zipfile.ZipFile(path, "r") as archive:
            return archive.namelist()
    except Exception:
        return []
