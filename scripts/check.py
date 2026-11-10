#!/usr/bin/env python3
"""Baseline generation/candidate checks plus independent small-grid oracle."""
import argparse, hashlib, json, pathlib, random, subprocess, sys
from png_pixels import decode, compare
PALETTE={0:(15,15,25),1:(0,210,255),2:(230,30,130),3:(255,200,0)}

def active(n,i,j):
    c=n//2
    return j<=max(i,n-1-i) and (i-c)**2+(j-c)**2<=c*c

def reference_stabilize(values):
    """Reverse-order full-square scan; one legal toppling per unstable visit."""
    n=len(values); g=[row[:] for row in values]
    cells=[(i,j) for i in range(n-1,-1,-1) for j in range(n-1,-1,-1) if active(n,i,j)]
    while True:
        changed=False
        for i,j in cells:
            if g[i][j]<4: continue
            changed=True; g[i][j]-=4
            for di,dj in ((1,0),(0,1),(-1,0),(0,-1)):
                ni,nj=i+di,j+dj
                if 0<=ni<n and 0<=nj<n: g[ni][nj]+=1
        if not changed: return g

def reference_identity(n):
    first=reference_stabilize([[6]*n for _ in range(n)])
    return reference_stabilize([[6-v for v in row] for row in first])

def load_grid(path):
    values=list(map(int,path.read_text().split())); n=values[0]
    if len(values)!=n*n+1: raise AssertionError('invalid grid dimensions')
    return [values[1+i*n:1+(i+1)*n] for i in range(n)]

def write_grid(path,grid):
    with path.open('x') as f:
        f.write(str(len(grid))+'\n')
        for row in grid: f.write(' '.join(map(str,row))+'\n')

def compare_grids(expected,actual):
    if len(expected)!=len(actual): raise AssertionError('grid sizes differ')
    for i,(a,b) in enumerate(zip(expected,actual)):
        for j,(x,y) in enumerate(zip(a,b)):
            if x!=y: raise AssertionError(f'integer mismatch at ({i},{j}): expected {x}, actual {y}')

def verify_grid_image(grid,png):
    n=len(grid); w,h,rgb=decode(png)
    if (w,h)!=(n,n): raise AssertionError('image dimensions differ from grid')
    expected=bytes(c for row in grid for v in row for c in PALETTE.get(v,(0,0,0)))
    if expected!=rgb: raise AssertionError('rendered image differs from exact integer-grid palette')
    for i in range(n):
        for j in range(n):
            if active(n,i,j) and not 0<=grid[i][j]<=3:
                raise AssertionError(f'active cell ({i},{j}) is not stable')

def run(command,directory):
    directory.mkdir()
    with (directory/'stdout.txt').open('w') as out,(directory/'stderr.txt').open('w') as err:
        subprocess.run(list(map(str,command)),cwd=directory,stdout=out,stderr=err,check=True)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--source',type=pathlib.Path,required=True)
    p.add_argument('--binary',type=pathlib.Path,required=True); p.add_argument('--output',type=pathlib.Path,required=True)
    p.add_argument('--reference-png',type=pathlib.Path,required=True)
    p.add_argument('--golden',type=pathlib.Path); p.add_argument('--target-png',type=pathlib.Path)
    p.add_argument('--sizes',nargs='+',type=int,default=[1,2,3,4,5,6,7,8,15,16,31,32,101,1001])
    a=p.parse_args()
    for key in ('source','binary','output','reference_png','golden','target_png'):
        if getattr(a,key): setattr(a,key,getattr(a,key).resolve())
    a.output.mkdir(); driver=a.output/'grid-driver.exe'
    command=['gcc','-O3','-g',f'-DSANDPILE_SOURCE="{a.source}"',str(pathlib.Path(__file__).resolve().parents[1]/'tests/grid_driver.c'),'-o',str(driver),'-lm']
    subprocess.run(command,check=True)
    checks=[]
    report={'source_sha256':hashlib.sha256(a.source.read_bytes()).hexdigest(),'adapter_build_command':command,'seed':598,'checks':checks}
    def save(): (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    try:
        for n in a.sizes:
            d=a.output/f'n{n}'; grid_path=d/'identity.grid'
            run([driver,'identity',n,grid_path],d); grid=load_grid(grid_path)
            verify_grid_image(grid,d/'identity.png')
            release=a.output/f'release-n{n}'
            if n==1001 and a.target_png:
                compare(d/'identity.png',a.target_png)
            else:
                run([a.binary,n],release); compare(d/'identity.png',release/'identity.png')
            if n<=32: compare_grids(reference_identity(n),grid)
            if a.golden:
                compare_grids(load_grid(a.golden/f'n{n}'/'identity.grid'),grid)
                compare(a.golden/f'n{n}'/'identity.png',d/'identity.png')
            entry={'kind':'identity','size':n,'all_allocated_cells_compared_to_oracle':n<=32,
                   'all_allocated_cells_compared_to_golden':bool(a.golden),'active_stability':'PASS','grid_palette':'PASS','release_adapter_pixels':'PASS'}
            if n==1001:
                try: entry['reference_comparison']=compare(a.reference_png,d/'identity.png')
                except AssertionError as e: entry['reference_comparison']={'status':'FAIL','error':str(e)}; report['reference_mismatch']=True
            checks.append(entry); save(); print(json.dumps(entry),flush=True)
        rng=random.Random(598)
        for trial in range(24):
            n=1+trial%8; initial=[[rng.randrange(20) if active(n,i,j) else rng.randrange(-9,10) for j in range(n)] for i in range(n)]
            inp=a.output/f'random-{trial}.grid'; write_grid(inp,initial)
            d=a.output/f'random-{trial}'; out=d/'stable.grid'
            run([driver,'stabilize',n,inp,out],d); grid=load_grid(out)
            compare_grids(reference_stabilize(initial),grid); verify_grid_image(grid,d/'identity.png')
            again=a.output/f'random-{trial}-again'; second=again/'stable.grid'
            run([driver,'stabilize',n,out,second],again); compare_grids(grid,load_grid(second))
            checks.append({'kind':'random-stabilization-and-idempotence','trial':trial,'size':n,'status':'PASS'})
        # Independent mathematical checks on active cells only: sink counters are not group elements.
        for n in range(1,9):
            e=reference_identity(n)
            recurrent=reference_stabilize([[3+rng.randrange(4) if active(n,i,j) else 0 for j in range(n)] for i in range(n)])
            for name,x in [('identity-idempotence',e),('recurrent-identity-action',recurrent)]:
                summed=[[x[i][j]+e[i][j] if active(n,i,j) else 0 for j in range(n)] for i in range(n)]
                result=reference_stabilize(summed)
                if any(result[i][j]!=x[i][j] for i in range(n) for j in range(n) if active(n,i,j)):
                    raise AssertionError(f'{name} failed at N={n}')
                checks.append({'kind':name,'size':n,'status':'PASS'})
        for k,args in enumerate([[],['0'],['-1'],['abc'],['12x'],['2147483648'],['2','extra']]):
            d=a.output/f'invalid-{k}'; d.mkdir()
            with (d/'stdout.txt').open('w') as out,(d/'stderr.txt').open('w') as err:
                result=subprocess.run([str(a.binary),*args],cwd=d,stdout=out,stderr=err)
            if result.returncode==0: raise AssertionError(f'invalid CLI accepted: {args}')
            checks.append({'kind':'invalid-cli','args':args,'status':'PASS'})
        report['status']='FAIL' if report.get('reference_mismatch') else 'PASS'; save()
        if report['status']!='PASS': raise SystemExit(1)
        print(f'PASS: {len(checks)} correctness checks',flush=True)
    except BaseException as e:
        report['status']='FAIL'; report['error']=str(e); save(); raise
if __name__=='__main__': main()
