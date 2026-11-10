/* Exhaustively compare interval membership with the exact starter predicate. */
#define main starter_main
#include SANDPILE_SOURCE
#undef main

int main(int argc, char **argv) {
  if (argc != 2) die("usage: row-mask-test N");
  N = atoi(argv[1]);
  // This test deliberately uses the starter's int predicate in its safe range.
  if (N < 1 || N > 4096) die("mask test supports sizes 1..4096");
  struct active_row *rows = precompute_active_rows();
  uint64_t active = 0, scanned = 0;
  for (int i = 0; i < N; ++i) {
    scanned += (uint64_t)MAX(i, N - 1 - i) + 1;
    for (int j = 0; j < N; ++j) {
      int expected = j <= MAX(i, N - 1 - i) &&
          (i - N / 2) * (i - N / 2) + (j - N / 2) * (j - N / 2) <=
              (N / 2) * (N / 2);
      int actual = rows[i].first <= j && j <= rows[i].last;
      if (actual != expected) {
        fprintf(stderr,"mask mismatch N=%d (%d,%d) interval=[%d,%d]\n",
                N,i,j,rows[i].first,rows[i].last);
        return 1;
      }
      active += actual;
    }
  }
  free(rows);
  printf("{\"size\":%d,\"cells_compared\":%"PRIu64",\"active_cells\":%"PRIu64",\"original_scan_cells\":%"PRIu64",\"mismatches\":0}\n",
         N,(uint64_t)N*N,active,scanned);
  return 0;
}
