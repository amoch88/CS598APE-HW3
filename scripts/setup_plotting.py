#!/usr/bin/env python3
"""Install only plotting dependencies in ignored results/plot-venv, without sudo."""
import argparse,hashlib,json,pathlib,subprocess,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--check-only',action='store_true');a=p.parse_args()
r=ROOT/'results';r.mkdir(exist_ok=True);env=r/'plot-venv';python=env/'bin/python'
if not a.check_only:
 if not python.exists():
  subprocess.run(['python3','-m','venv','--without-pip',str(env)],check=True)
  bootstrap=r/'get-pip.py'
  if not bootstrap.exists():bootstrap.write_bytes(urllib.request.urlopen('https://bootstrap.pypa.io/get-pip.py',timeout=30).read())
  (r/'plot-bootstrap.json').write_text(json.dumps({'url':'https://bootstrap.pypa.io/get-pip.py','sha256':hashlib.sha256(bootstrap.read_bytes()).hexdigest()},indent=2)+'\n')
  subprocess.run([str(python),str(bootstrap)],check=True,timeout=180)
 subprocess.run([str(python),'-m','pip','install','-r',str(ROOT/'scripts/plot-requirements.txt')],check=True,timeout=180)
subprocess.run([str(python),'-c','import matplotlib,numpy; print("matplotlib",matplotlib.__version__,"numpy",numpy.__version__)'],check=True)
print(python)
