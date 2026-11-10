#include <errno.h>
#include <inttypes.h>
#include <math.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

#define MIN(a, b) (((a) < (b)) ? (a) : (b))
#define MAX(a, b) (((a) > (b)) ? (a) : (b))

static void die(const char *s) {
  fprintf(stderr, "%s\n", s);
  exit(1);
}

int N = 801;
int **grid;

// you can also use this function to debug print your sandpile
static void render(char *filename) {
  int chan = 3;
  unsigned char *pixels = (unsigned char *)malloc(N * N * chan * sizeof(char));
  int stride = N * chan;
  if (!pixels)
    die("malloc failed for PNG pixel buffer");
  for (int i = 0; i < N; ++i) {
    for (int j = 0; j < N; ++j) {
      unsigned char r = 0, g = 0, b = 0;
      switch (grid[i][j]) {
      case 0: // obsidian
        r = 15;
        g = 15;
        b = 25;
        break;
      case 1: // electric cyan
        r = 0;
        g = 210;
        b = 255;
        break;
      case 2: // vibrant magenta
        r = 230;
        g = 30;
        b = 130;
        break;
      case 3: // bright gold
        r = 255;
        g = 200;
        b = 0;
        break;
      default: // white
        r = 0;
        g = 0;
        b = 0;
      }

      int pid = (i * N + j) * chan;
      pixels[pid] = r;
      pixels[pid + 1] = g;
      pixels[pid + 2] = b;
    }
  }
  if (stbi_write_png(filename, N, N, chan, pixels, stride)) {
    printf("Successfully saved sandpile identity to: %s\n", filename);
  } else {
    die("Error: stb_image_write failed to save png file\n");
  }
  free(pixels);
}

struct active_row {
  int first;
  int last;
};

// The disk intersects each row in one interval; intersecting with the original
// mouth prefix keeps it contiguous. Widen before squaring to avoid overflow.
static struct active_row *precompute_active_rows(void) {
  struct active_row *rows = malloc((size_t)N * sizeof(*rows));
  if (!rows)
    die("malloc failed for active row intervals");
  int64_t center = N / 2;
  int64_t radius_squared = center * center;
  for (int i = 0; i < N; ++i) {
    rows[i].first = 0;
    rows[i].last = -1;
    int64_t di = (int64_t)i - center;
    for (int j = 0; j <= MAX(i, N - 1 - i); ++j) {
      int64_t dj = (int64_t)j - center;
      if (di * di + dj * dj <= radius_squared) {
        if (rows[i].last < 0)
          rows[i].first = j;
        rows[i].last = j;
      }
    }
  }
  return rows;
}

struct queued_cell { int i, j; };
struct frontier {
  struct queued_cell *cells;
  unsigned char *scheduled;
  const struct active_row *rows;
  size_t head, tail, pending, capacity;
};

static void add_grains(int *cell, int q) {
  if (*cell > INT_MAX - q)
    die("integer overflow in grain accumulation");
  *cell += q;
}

// At most one entry per active cell; storage is bounded by active domain size.
static void schedule(struct frontier *f, int i, int j) {
  if (j < f->rows[i].first || j > f->rows[i].last || grid[i][j] < 4)
    return;
  size_t id = (size_t)i * (size_t)N + (size_t)j;
  if (f->scheduled[id])
    return;
  if (f->pending == f->capacity)
    die("worklist capacity invariant violated");
  f->scheduled[id] = 1;
  f->cells[f->tail] = (struct queued_cell){i,j};
  if (++f->tail == f->capacity) f->tail = 0;
  ++f->pending;
}

static void receive(struct frontier *f, int i, int j, int q) {
  add_grains(&grid[i][j],q); // Includes inactive sink counters.
  schedule(f,i,j);
}

static void stabilize() {
  struct active_row *rows = precompute_active_rows();
  size_t capacity = 0;
  for (int i=0;i<N;++i)
    if (rows[i].last >= rows[i].first)
      capacity += (size_t)(rows[i].last - rows[i].first + 1);
  if (!capacity || capacity > SIZE_MAX / sizeof(struct queued_cell))
    die("invalid worklist capacity");
  struct frontier f = {0};
  f.rows = rows; f.capacity = capacity;
  f.cells = malloc(capacity * sizeof(*f.cells));
  f.scheduled = calloc((size_t)N * (size_t)N, sizeof(*f.scheduled));
  if (!f.cells || !f.scheduled) die("worklist allocation failed");
  for (int i=0;i<N;++i)
    for (int j=rows[i].first;j<=rows[i].last;++j)
      schedule(&f,i,j);
  size_t pending = f.pending;
  while (pending) {
    struct queued_cell cell = f.cells[f.head];
    if (++f.head == capacity) f.head = 0;
    --f.pending;
    int i = cell.i, j = cell.j;
    f.scheduled[(size_t)i * (size_t)N + (size_t)j] = 0;
    // Scheduled heights cannot decrease before their unique entry is popped.
    int q = grid[i][j] / 4;
    grid[i][j] -= 4 * q;
    if (i > 0) receive(&f,i-1,j,q);
    if (j > 0) receive(&f,i,j-1,q);
    if (i < N-1) receive(&f,i+1,j,q);
    if (j < N-1) receive(&f,i,j+1,q);
    // Unit mode may leave this cell unstable; batched mode leaves a remainder.
    schedule(&f,i,j);
    pending = f.pending;
  }
  free(f.scheduled);
  free(f.cells);
  free(rows);
}

void find_identity() {
  for (int i = 0; i < N; ++i) {
    for (int j = 0; j < N; ++j) {
      grid[i][j] = 6;
    }
  }
  stabilize();
  for (int i = 0; i < N; ++i) {
    for (int j = 0; j < N; ++j) {
      grid[i][j] = 6 - grid[i][j];
    }
  }
  stabilize();
}

int main(int argc, char **argv) {
  if (argc < 2 || argc > 2) {
    fprintf(stderr, "Usage: %s N\n", argv[0]);
    return EXIT_FAILURE;
  }
  char *end;
  uintmax_t parsed = strtoumax(argv[1], &end, 10);
  if (errno || argv[1][0] < '0' || argv[1][0] > '9' || *end || !parsed ||
      parsed > INT32_MAX)
    die("grid size must be a positive int");
  N = (int)parsed;

  grid = (int **)malloc(N * sizeof(int *));
  for (int i = 0; i < N; ++i) {
    grid[i] = (int *)malloc(N * sizeof(int));
  }

  find_identity();

  render("identity.png");
  for (int i = 0; i < N; ++i) {
    free(grid[i]);
  }
  free(grid);
  return EXIT_SUCCESS;
}
