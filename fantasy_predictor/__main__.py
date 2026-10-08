"""Command-line entry point: ``python -m fantasy_predictor <match_number>``."""
import argparse

from .pipeline import run


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m fantasy_predictor",
        description="Predict the best Dream11 XI for an IPL 2025 match.",
    )
    parser.add_argument("match_number", type=int, help="IPL 2025 match number (playoffs are 71-74)")
    args = parser.parse_args(argv)
    run(args.match_number)


if __name__ == "__main__":
    main()
