# repocity

Turn any codebase into an explorable **3D city**.

Point repocity at a local git repository and it generates a single HTML file:
a city where every file is a building, every folder is a district, and you can
fly around your codebase, hover any building to see what it is, and instantly
spot the parts of the code that are huge, old, or changing fast.

![mapping](https://img.shields.io/badge/buildings-files-blue)
![keys](https://img.shields.io/badge/api%20keys-none-green)

## The mapping

| City element | Code element |
|---|---|
| Building | One source file |
| Building height | Lines of code (log scale) |
| Building footprint | Lines of code (square-root scale) |
| Building color | Recency — warm = changed recently, cool = untouched for a long time |
| District (ground plate) | Top-level folder |
| District label | Folder name, floating over the district |

## No keys, no accounts, no network (for analysis)

repocity never talks to GitHub, never needs a token, and never uploads your
code anywhere. It reads a checkout **on your own disk** using `git log`, which
runs locally. The generated HTML page loads Three.js from a CDN so you can open
it in any browser; the city data itself is embedded in the page. If you want a
fully offline viewer, swap the CDN import for a local Three.js build — the data
format is plain JSON (see `city.json` below).

## Install

Requires Python 3.9+ and git. No third-party dependencies.

```bash
pip install repocity
# or, from source:
git clone https://github.com/Arnav38025/repocity.git
cd repocity
pip install -e .
```

## Use it

```bash
# Build a city from any repo on your disk:
repocity /path/to/your-repo -o city.html

# Then just open city.html in a browser. Drag to orbit, scroll to zoom,
# hover a building for details, use the search box to find a file.

# Emit just the data (for your own visualizers):
repocity /path/to/your-repo --json -o city.json
```

### Options

```
repocity PATH [options]
  -o, --output FILE     Output file (default: city.html, or city.json with --json)
  --json                Emit raw city data as JSON instead of the HTML viewer
  --max-files N         Only include the N largest files (default: 2000)
  --include-hidden      Include dotfiles and dot-directories (skipped by default)
  --no-git              Ignore git history; use file modification times for recency
  --exclude GLOB        Skip paths matching GLOB (repeatable)
```

## What it skips

By default repocity skips `.git`, `node_modules`, `__pycache__`, virtual
environments, and generated/minified artifacts (`*.min.js`, `*.map`,
`package-lock.json`, `*.pyc`, images, fonts, archives). Everything else that
looks like text is included. Use `--exclude` to add your own patterns.

## How recency color works

Each file's color comes from its most recent commit:

| Last changed | Color |
|---|---|
| Within 7 days | Bright amber |
| Within 30 days | Orange |
| Within 90 days | Teal |
| Within a year | Blue |
| Over a year ago / no git history | Slate grey |

So a city that's mostly grey has a lot of code nobody has touched in a long
time — and the glowing amber towers are where the action is.

## How it works

1. **Analyze** (`repocity/analyze.py`) — walks the tree, counts non-blank
   lines per text file, and runs `git log` once to get per-file commit counts
   and last-commit dates. Falls back to file modification times when the
   directory isn't a git repo.
2. **Layout** (`repocity/render.py`) — groups files into districts by
   top-level folder, sorts by size, and packs buildings onto a deterministic
   grid (same repo → same city, every time).
3. **Render** — writes a standalone HTML viewer (Three.js) with orbit
   controls, hover tooltips, search, and district labels. Or `--json` for just
   the data.

## Development

```bash
python -m unittest discover -s tests -v
```

## License

MIT. See [LICENSE](LICENSE).
