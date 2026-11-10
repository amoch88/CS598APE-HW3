/* Test-only adapter: include the specified implementation, expose its grid. */
#define main starter_main
#include SANDPILE_SOURCE
#undef main
#include <time.h>

static double adapter_now(void) {
  struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t);
  return (double)t.tv_sec + (double)t.tv_nsec / 1e9;
}

int main(int argc, char **argv) {
  if (argc != 4 && argc != 5) die("identity N output.grid | stabilize N input.grid output.grid");
  N = atoi(argv[2]);
  if (N < 1 || N > 1001) die("test adapter supports sizes 1..1001");
#ifdef SANDPILE_GRID_ALLOCATORS
  allocate_grid();
#else
  grid = malloc((size_t)N * sizeof(*grid));
  if (!grid) die("allocation failed");
  for (int i=0;i<N;i++) {
    grid[i] = malloc((size_t)N * sizeof(**grid));
    if (!grid[i]) die("allocation failed");
  }
#endif
  double compute_started=adapter_now();
  const char *output;
  if (!strcmp(argv[1], "identity") && argc == 4) {
    find_identity(); output = argv[3];
  } else if (!strcmp(argv[1], "stabilize") && argc == 5) {
    FILE *f=fopen(argv[3],"r"); int size;
    if (!f || fscanf(f,"%d",&size)!=1 || size!=N) die("bad input grid");
    for(int i=0;i<N;i++) for(int j=0;j<N;j++)
      if(fscanf(f,"%d",&grid[i][j])!=1) die("truncated input grid");
    fclose(f); stabilize(); output=argv[4];
  } else die("invalid test adapter arguments");
  double compute_seconds=adapter_now()-compute_started;
  double dump_started=adapter_now();
  FILE *f=fopen(output,"wx"); if(!f) die("cannot create new grid output");
  fprintf(f,"%d\n",N);
  for(int i=0;i<N;i++) {
    for(int j=0;j<N;j++) fprintf(f,"%d%c",grid[i][j],j==N-1?'\n':' ');
  }
  if(fclose(f)) die("grid output failed");
  double dump_seconds=adapter_now()-dump_started;
  double render_started=adapter_now();
  render("identity.png");
  double render_seconds=adapter_now()-render_started;
  FILE *timing=fopen("adapter-times.json","wx");
  if(!timing) die("cannot create adapter timing");
  fprintf(timing,"{\"size\":%d,\"computation_seconds\":%.9f,\"grid_dump_seconds\":%.9f,\"render_seconds\":%.9f}\n",N,compute_seconds,dump_seconds,render_seconds);
  if(fclose(timing)) die("cannot write adapter timing");
#ifdef SANDPILE_GRID_ALLOCATORS
  release_grid();
#else
  for(int i=0;i<N;i++) free(grid[i]); free(grid);
#endif
  return 0;
}
