import argparse
import json
import sys
from pathlib import Path

from . import core


def main(argv=None):
    # Allow an optional leading "analyze" subcommand.
    args_list = list(argv) if argv is not None else list(sys.argv[1:])
    if args_list and args_list[0] == "analyze":
        args_list = args_list[1:]
    parser = argparse.ArgumentParser(prog="review-analysis")
    parser.add_argument("input")
    parser.add_argument("--out-md", default=None)
    parser.add_argument("--out-json", default=None)
    args = parser.parse_args(args_list)

    try:
        reviews = core.load_reviews(args.input)
        report = core.analyze(reviews)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print("error: %s" % e, file=sys.stderr)
        sys.exit(1)

    md = core.render_markdown(report)
    js = json.dumps(report, indent=2)

    if args.out_md:
        Path(args.out_md).write_text(md, encoding="utf-8")
    else:
        print(md)
    if args.out_json:
        Path(args.out_json).write_text(js, encoding="utf-8")
    sys.exit(0)


if __name__ == "__main__":
    main()