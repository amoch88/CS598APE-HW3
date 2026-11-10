#!/usr/bin/env python3
"""Generate a disposable instrumented copy; never edit production sandpile.c."""
import argparse, difflib, hashlib, pathlib
EXPECTED='15fe837445b8e32a15ac61fcfa388980b54d9173'
SUPPORT=r'''
#include <time.h>
struct phase_stats { uint64_t sweeps, topples, qhist[9]; int max_height; double seconds; };
static struct phase_stats phases[2];
static int phase_next;
static double render_seconds;
static double now_seconds(void) {
  struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t);
  return (double)t.tv_sec + (double)t.tv_nsec / 1e9;
}
static void dump_phase(int phase) {
  char name[32]; snprintf(name,sizeof(name),"phase-%d.grid",phase+1);
  FILE *f=fopen(name,"wx"); if(!f) die("cannot create phase grid");
  fprintf(f,"%d\n",N);
  for(int i=0;i<N;i++) {
    for(int j=0;j<N;j++) fprintf(f,"%d%c",grid[i][j],j==N-1?'\n':' ');
  }
  if(fclose(f)) die("cannot write phase grid");
}
static void print_diagnostics(void) {
  uint64_t scan=0, active=0;
  for(int i=0;i<N;i++) for(int j=0;j<=MAX(i,N-1-i);j++) {
    scan++;
    if((i-N/2)*(i-N/2)+(j-N/2)*(j-N/2)<=(N/2)*(N/2)) active++;
  }
  FILE *f=fopen("diagnostics.json","wx"); if(!f) die("cannot create diagnostics");
  fprintf(f,"{\"size\":%d,\"scan_cells_per_sweep\":%"PRIu64",\"active_cells\":%"PRIu64",\"render_seconds\":%.9f,\"phases\":[",N,scan,active,render_seconds);
  for(int k=0;k<2;k++) {
    struct phase_stats *d=&phases[k];
    fprintf(f,"%s{\"phase\":%d,\"seconds\":%.9f,\"sweeps\":%"PRIu64",\"scan_visits\":%"PRIu64",\"active_visits\":%"PRIu64",\"unit_topplings\":%"PRIu64",\"max_height_at_visit\":%d,\"q_histogram_0_to_7_then_8plus\":[",k?",":"",k+1,d->seconds,d->sweeps,scan*d->sweeps,active*d->sweeps,d->topples,d->max_height);
    for(int q=0;q<9;q++) fprintf(f,"%s%"PRIu64,q?",":"",d->qhist[q]);
    fprintf(f,"]}");
  }
  fprintf(f,"]}\n"); if(fclose(f)) die("cannot write diagnostics");
}
'''

def replace_once(text,old,new):
    if text.count(old)!=1: raise ValueError(f'expected exactly one instrumentation anchor: {old!r}')
    return text.replace(old,new,1)

def main():
    p=argparse.ArgumentParser(); p.add_argument('source',type=pathlib.Path); p.add_argument('output',type=pathlib.Path)
    a=p.parse_args(); original=a.source.read_text(); text=original
    support=SUPPORT
    row_intervals='precompute_active_rows' in original
    if row_intervals:
        support=support.replace('  FILE *f=fopen("diagnostics.json","wx");', '  scan=active; // interval traversal visits only active cells\n  FILE *f=fopen("diagnostics.json","wx");')
    text=replace_once(text,'static void stabilize() {',support+'\nstatic void stabilize() {\n  int phase=phase_next++;\n  struct phase_stats *d=&phases[phase];\n  double started=now_seconds();')
    text=replace_once(text,'    changed = 0;\n','    changed = 0;\n    d->sweeps++;\n')
    indent='        ' if row_intervals else '          '
    text=replace_once(text,indent+'changed = 1; // topple it',
        indent+'d->topples++;\n'+indent+'int q=grid[i][j]/4;\n'+indent+'d->qhist[q<8?q:8]++;\n'+
        indent+'if(grid[i][j]>d->max_height) d->max_height=grid[i][j];\n'+indent+'changed = 1; // topple it')
    ending='  } while (changed);\n  free(rows);\n}' if row_intervals else '  } while (changed);\n}'
    text=replace_once(text,ending,ending[:-1]+'  d->seconds=now_seconds()-started;\n  dump_phase(phase);\n}')
    text=replace_once(text,'  render("identity.png");','  double render_started=now_seconds();\n  render("identity.png");\n  render_seconds=now_seconds()-render_started;\n  print_diagnostics();')
    with a.output.open('x') as f: f.write(text)
    with a.output.with_suffix('.diff').open('x') as f:
        f.writelines(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile=str(a.source),tofile=str(a.output)))
    print('source_sha256='+hashlib.sha256(original.encode()).hexdigest())
if __name__=='__main__': main()
