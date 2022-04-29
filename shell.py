import lang
import sys

fn = sys.argv[1]

with open(fn, 'r') as f:
    lines = f.read()
    output, error = lang.run(fn, lines)
    if error: print(error)


