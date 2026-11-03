import argparse
from .build import build

parser = argparse.ArgumentParser()
parser.add_argument('command', choices=['build'])
parser.add_argument('--runtime', help='validated cohort runtime (defaults to THESIS_RUNTIME or the worktree runtime)')
parser.add_argument('--out', help='output directory (defaults to the worktree runtime a_p2/inputs)')
args = parser.parse_args()
build(runtime=args.runtime, out=args.out)
