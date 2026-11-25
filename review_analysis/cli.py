import argparse
import json
import sys
from pathlib import Path

from . import converters, core


def main(argv=None):
    # Allow an optional leading subcommand ("analyze" is the default).
    args_list = list(argv) if argv is not None else list(sys.argv[1:])
    cmd = "analyze"
    if args_list and args_list[0] in ("analyze", "convert"):
        cmd = args_list.pop(0)

    if cmd == "convert":
        parser = argparse.ArgumentParser(prog="review-analysis convert")
        parser.add_argument("input")
        parser.add_argument("--source", default=None,
                            help="export format: one of %s; omit to auto-detect "
                                 "it from the CSV headers"
                                 % ", ".join(sorted(converters.FIELD_ALIASES)))
        parser.add_argument("--out", required=True)
        args = parser.parse_args(args_list)
        try:
            n, source = converters.convert_file(args.input, args.source, args.out)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print("error: %s" % e, file=sys.stderr)
            sys.exit(1)
        how = "" if args.source not in (None, "auto") else " (auto-detected)"
        print("converted %d reviews from %s export%s to %s"
              % (n, source, how, args.out))
        sys.exit(0)

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