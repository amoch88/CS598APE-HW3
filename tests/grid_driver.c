/* Test-only adapter: include the unchanged implementation, expose its grid. */
#define main starter_main
#include SANDPILE_SOURCE
#undef main

int main(int argc, char **argv) {
  if (argc != 4 && argc != 5) die("identity N output.grid | stabilize N input.grid output.grid");
  N = atoi(argv[2]);
  if (N < 1 || N > 1001) die("test adapter supports sizes 1..1001");
  grid = malloc((size_t)N * sizeof(*grid));
  if (!grid) die("allocation failed");
  for (int i=0;i<N;i++) {
    grid[i] = malloc((size_t)N * sizeof(**grid));
    if (!grid[i]) die("allocation failed");
  }
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
  FILE *f=fopen(output,"wx"); if(!f) die("cannot create new grid output");
  fprintf(f,"%d\n",N);
  for(int i=0;i<N;i++) {
    for(int j=0;j<N;j++) fprintf(f,"%d%c",grid[i][j],j==N-1?'\n':' ');
  }
  if(fclose(f)) die("grid output failed");
  render("identity.png");
  for(int i=0;i<N;i++) free(grid[i]); free(grid);
  return 0;
}
