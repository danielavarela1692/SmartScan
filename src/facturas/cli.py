import argparse
from pathlib import Path

from .config import settings
from .ingestion import EmailSource, ManualSource
from .pipeline import run


def build_source(args: argparse.Namespace):
    if args.source == "manual":
        return ManualSource(Path(args.path))
    return EmailSource(
        host=settings.imap_host,
        user=settings.imap_user,
        password=settings.imap_password,
        folder=settings.imap_folder,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--source", choices=["manual", "email"], default="manual")
    run_parser.add_argument("--path", default="./inbox")

    args = parser.parse_args()
    source = build_source(args)

    for result in run(source):
        if result.errors:
            print(f"[REVISION] {result.document.filename}: {'; '.join(result.errors)}")
        else:
            print(f"[OK] {result.document.filename} -> {result.service_expense.cuit} / {result.service_expense.number}")


if __name__ == "__main__":
    main()
