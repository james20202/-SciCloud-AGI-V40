import os, shutil, sys, time
from pathlib import Path

def main():
    if len(sys.argv) < 4: return 2
    source, target, backup = map(Path, sys.argv[1:4])
    time.sleep(1.5)
    backup.mkdir(parents=True, exist_ok=True)
    preserve = {'data','projects','output','logs','backups','__pycache__'}
    for name in ['core','ui','modules','main.py','requirements.txt','README.md','install.command','launch.command','apply_update.py']:
        p=target/name
        if p.exists():
            dest=backup/name
            if p.is_dir(): shutil.copytree(p,dest,dirs_exist_ok=True)
            else: shutil.copy2(p,dest)
    items=list(source.iterdir())
    if len(items)==1 and items[0].is_dir() and (items[0]/'main.py').exists(): source=items[0]
    for p in source.iterdir():
        if p.name in preserve: continue
        dest=target/p.name
        if p.is_dir(): shutil.copytree(p,dest,dirs_exist_ok=True)
        else: shutil.copy2(p,dest)
    mainpy=target/'main.py'
    if mainpy.exists():
        os.execv(sys.executable,[sys.executable,str(mainpy)])
    return 0
if __name__=='__main__': raise SystemExit(main())
