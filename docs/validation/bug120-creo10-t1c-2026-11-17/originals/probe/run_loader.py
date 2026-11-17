import json, subprocess, sys
from pathlib import Path
ROOT=Path(r'D:/my/MCP_CREO_MechDog')
sys.path.insert(0,str(ROOT))
from bridge import native_environment, toolkit_lock
case=Path(sys.argv[1]).resolve()
exe=ROOT/'test_runs'/'2026-11-17_t1c_closure'/'probe'/'t1c_load.exe'
with toolkit_lock(wait_seconds=60, operation='t1c_load:'+case.name):
    p=subprocess.run([str(exe), str(case)], capture_output=True, text=True, timeout=600, cwd=str(case), env=native_environment())
print('rc', p.returncode, p.stderr[-500:])
