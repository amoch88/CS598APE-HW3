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
#define SANDPILE_GRID_ALLOCATORS 1
static int *grid_storage;

static void allocate_grid(void) {
  size_t n = (size_t)N;
  if (n > SIZE_MAX / sizeof(*grid) || n > SIZE_MAX / n / sizeof(**grid))
    die("grid allocation size overflow");
  grid_storage = malloc(n * n * sizeof(*grid_storage));
  if (!grid_storage) die("grid storage allocation failed");
  grid = malloc(n * sizeof(*grid));
  if (!grid) { free(grid_storage); die("grid row allocation failed"); }
  for (int i=0;i<N;++i) grid[i] = grid_storage + (size_t)i*n;
}

static void release_grid(void) {
  free(grid_storage);
  free(grid);
}

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

// Positive increments are checked before addition; q*4 cannot exceed the
// current nonnegative int height. Inactive cells retain their sink counters.
static void add_grains(int *cell, int q) {
  if (*cell > INT_MAX - q)
    die("integer overflow in grain accumulation");
  *cell += q;
}

static void stabilize_checked(const struct active_row *rows) {
  int changed = 0;
  do {
    changed = 0;
    for (int i = 0; i < N; ++i) {
      for (int j = rows[i].first; j <= rows[i].last; ++j) {
        if (grid[i][j] < 4)
          continue;
        changed = 1; // topple it
        // q successive topplings are legal: before the last, height >= 4.
        int q = grid[i][j] / 4;
        grid[i][j] -= 4 * q;
        if (i > 0)
          add_grains(&grid[i - 1][j], q);
        if (j > 0)
          add_grains(&grid[i][j - 1], q);
        if (i < N - 1)
          add_grains(&grid[i + 1][j], q);
        if (j < N - 1)
          add_grains(&grid[i][j + 1], q);
      }
    }
  } while (changed);
}

static void stabilize_bounded(const struct active_row *rows) {
  int changed = 0;
  do {
    changed = 0;
    for (int i = 0; i < N; ++i) {
      for (int j = rows[i].first; j <= rows[i].last; ++j) {
        if (grid[i][j] < 4)
          continue;
        changed = 1; // topple it
        // q successive topplings are legal: before the last, height >= 4.
        int q = grid[i][j] / 4;
        grid[i][j] -= 4 * q;
        if (i > 0)
          grid[i - 1][j] += q;
        if (j > 0)
          grid[i][j - 1] += q;
        if (i < N - 1)
          grid[i + 1][j] += q;
        if (j < N - 1)
          grid[i][j + 1] += q;
      }
    }
  } while (changed);
}

// Legal topplings cannot increase the sum of positive cell heights:
// subtracting 4*q removes 4*q positive grains, and at most four recipients
// gain q each (including negative sink counters). If that initial sum fits
// int, every subsequent cell value fits int. Negative cells only increase.
// Keep checked updates for arbitrary test inputs outside this sufficient bound.
static void stabilize() {
  struct active_row *rows = precompute_active_rows();
  int64_t positive = 0;
  for (int i=0;i<N && positive<=INT_MAX;++i)
    for (int j=0;j<N && positive<=INT_MAX;++j)
      if (grid[i][j]>0) positive += grid[i][j];
  if (positive<=INT_MAX)
    stabilize_bounded(rows);
  else
    stabilize_checked(rows);
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

  allocate_grid();

  find_identity();

  render("identity.png");
  release_grid();
  return EXIT_SUCCESS;
}
