#!/usr/bin/env python3
"""Clean rebuild, binary identity, mask and post-rebuild correctness checks."""
import argparse,hashlib,json,pathlib,subprocess,sys
from png_pixels import compare
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('study',type=pathlib.Path);a=p.parse_args();r=a.study.resolve()
manifest=json.loads((r/'manifest.json').read_text());b=pathlib.Path(manifest['baseline']);row=pathlib.Path(manifest['row_results'])
goldens=row/'expected' if (row/'expected').is_dir() else r/'expected'
source=r/'source/sandpile.c';binary=r/'source/sandpile.exe';original=json.loads((r/'build-hashes.json').read_text())
def digest(x):return hashlib.sha256(x.read_bytes()).hexdigest()
assert digest(source)==original['source']
with (r/'final-clean-build.log').open('x') as f:subprocess.run(['make','clean','all'],cwd=source.parent,stdout=f,stderr=subprocess.STDOUT,check=True)
assert digest(binary)==original['binary'],'clean rebuild changed executable; revalidate target before acceptance'
report={'source_commit':manifest['source_commit'],'source_sha256':digest(source),'binary_sha256':digest(binary),'clean_rebuild_bit_identical':True}
d=r/'post-rebuild-correctness'
with (r/'post-rebuild-correctness.log').open('x') as f:
 subprocess.run(['taskset','-c','0',sys.executable,str(ROOT/'scripts/check.py'),'--source',str(source),'--binary',str(binary),'--output',str(d),'--reference-png',str(b/'source/identity-ref.png'),'--golden',str(goldens),'--sizes','1','2','3','4','5','6','7','8','15','16','31','32','101'],stdout=f,stderr=subprocess.STDOUT,check=True)
report['post_rebuild_correctness']=json.loads((d/'report.json').read_text())['status']
mask=r/'bin/final-mask.exe'
subprocess.run(['gcc','-O3','-g','-Werror',f'-DSANDPILE_SOURCE="{source}"',str(ROOT/'tests/row_intervals_driver.c'),'-o',str(mask),'-lm'],check=True)
sizes=sorted(set(range(1,129))|{250,251,252,500,501,502,999,1000,1001,1002})
checks=[json.loads(subprocess.check_output(['taskset','-c','0',str(mask),str(n)],text=True)) for n in sizes]
assert all(x['mismatches']==0 for x in checks)
report['mask']={'sizes':sizes,'total_positions':sum(x['cells_compared'] for x in checks),'checks':checks,'status':'PASS'}
if 'stabilize_bounded' in source.read_text():subprocess.run([sys.executable,str(ROOT/'scripts/check_overflow.py'),'--driver',str(d/'grid-driver.exe'),'--output',str(r/'post-rebuild-overflow')],check=True)
report['target_integer_report']=json.loads((r/'target-correctness/report.json').read_text())['status']
report['target_image_comparisons']=[]
for path in sorted((r/'timing').glob('n1001-run*/identity.png')):
 report['target_image_comparisons'].append({'path':str(path),'comparison':compare(b/'source/identity-ref.png',path)})
assert report['target_integer_report']=='PASS'
report['status']='PASS';(r/'final-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS: clean rebuild is byte-identical to the target-validated executable; post-rebuild checks passed')
