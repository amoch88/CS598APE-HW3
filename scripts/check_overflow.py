#!/usr/bin/env python3
"""Exercise the bounded and checked batching paths without enormous workloads."""
import argparse,json,pathlib,subprocess
from check import write_grid,load_grid,compare_grids,reference_stabilize
p=argparse.ArgumentParser();p.add_argument('--driver',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True)
a=p.parse_args();driver=a.driver.resolve();root=a.output.resolve();root.mkdir();maximum=2147483647
cases=[('bounded-large-quotient',[[maximum]],[[3]]),('checked-fallback',[[maximum-100,40],[40,40]],None),('negative-sinks',[[-maximum,6],[6,6]],None)]
checks=[]
for name,initial,expected in cases:
    d=root/name;d.mkdir();inp=d/'input.grid';out=d/'output.grid';write_grid(inp,initial)
    result=subprocess.run([str(driver),'stabilize',str(len(initial)),str(inp),str(out)],cwd=d,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
    compare_grids(expected if expected is not None else reference_stabilize(initial),load_grid(out))
    checks.append(dict(name=name,status='PASS',initial_positive_sum=sum(max(0,v) for line in initial for v in line)))
d=root/'overflow-rejection';d.mkdir();inp=d/'input.grid';write_grid(inp,[[maximum,4],[0,0]])
result=subprocess.run([str(driver),'stabilize','2',str(inp),str(d/'output.grid')],cwd=d,capture_output=True,text=True,timeout=30)
assert result.returncode!=0 and 'integer overflow in grain accumulation' in result.stderr
checks.append(dict(name='overflow-rejection',status='PASS',exit_status=result.returncode,stderr=result.stderr))
(root/'report.json').write_text(json.dumps(dict(status='PASS',checks=checks),indent=2)+'\n')
print('PASS: four overflow-bound/fallback cases')
