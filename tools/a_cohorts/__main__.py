"""Inspect, build and validate local simple cohort products."""
import argparse
import json
from .core import SUPPORTED_COHORTS, check_allowed, load, registry, validate


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list')
    for name in ('load', 'validate'):
        command = sub.add_parser(name)
        group = command.add_mutually_exclusive_group(required=True)
        group.add_argument('--cohort')
        if name == 'load':
            group.add_argument('--all', action='store_true')
    sub.add_parser('build')
    sub.add_parser('catalog')
    args = parser.parse_args()
    try:
        if args.command == 'list':
            result = list(registry().values())
        elif args.command == 'catalog':
            from .catalog import build_catalog
            result = build_catalog()
        elif args.command == 'build':
            result = {}
            for cohort in registry():
                if cohort not in SUPPORTED_COHORTS:
                    result[cohort] = {'status': 'NOT_SUPPORTED'}
                    continue
                try:
                    check_allowed(cohort)
                except ValueError:
                    continue
                try:
                    manifest = load(cohort)
                    result[cohort] = {'status': manifest['status'], 'patients': manifest['patients'], 'genes': manifest['genes']}
                except (KeyError, StopIteration):
                    result[cohort] = {'status': 'UNAVAILABLE', 'reason': 'Required source field or row is missing'}
                except (ValueError, OSError) as exc:
                    result[cohort] = {'status': 'UNAVAILABLE', 'reason': str(exc)}
            from .catalog import build_catalog
            result = {'build': result, 'catalog': build_catalog(build_results=result)}
        elif args.command == 'load' and args.all:
            result = {}
            for cohort in sorted(SUPPORTED_COHORTS):
                try:
                    result[cohort] = load(cohort)
                except (ValueError, OSError, KeyError, StopIteration) as exc:
                    result[cohort] = {'status': 'BLOCKED', 'reason': str(exc)}
        else:
            result = (load if args.command == 'load' else validate)(args.cohort)
        print(json.dumps(result, sort_keys=True))
    except (KeyError, StopIteration):
        parser.exit(1, 'Required source field or row is missing\n')
    except (ValueError, OSError) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()
