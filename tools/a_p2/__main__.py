import argparse
from .build import build

parser = argparse.ArgumentParser()
parser.add_argument('command', choices=['build'])
parser.parse_args()
build()
