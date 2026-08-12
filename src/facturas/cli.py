import argparse
import json
from pathlib import Path

from .config import settings
from .ingestion import EmailSource, ManualSource
from .matching import MatchOutcome, MatchStore, get_items_catalog_client
from .pipeline import process_document, resolve_concepts


def build_source(args: argparse.Namespace):
    if args.source == "manual":
        return ManualSource(Path(args.path))
    return EmailSource(
        host=settings.imap_host,
        user=settings.imap_user,
        password=settings.imap_password,
        folder=settings.imap_folder,
    )


def cmd_run(args: argparse.Namespace) -> None:
    source = build_source(args)
    for document in source.fetch_new():
        result = process_document(document)
        if result.errors:
            print(f"[REVISION] {document.filename}: {'; '.join(result.errors)}")
        else:
            print(f"[OK] {document.filename} -> {result.service_expense.cuit} / {result.service_expense.number}")


def _resolve_interactively(cuit: str, outcome: MatchOutcome, store: MatchStore) -> str | None:
    print(f'    Sin match: "{outcome.item.detail}"')
    if not outcome.candidates:
        print("    (no hay items de compra cargados para este proveedor en el catalogo)")
        return None

    for i, candidate in enumerate(outcome.candidates, start=1):
        print(f"      {i}. {candidate.description}")

    choice = input("    Elegi un numero (Enter para dejarlo pendiente): ").strip()
    if not choice:
        return None

    try:
        selected = outcome.candidates[int(choice) - 1]
    except (ValueError, IndexError):
        print("    Opcion invalida, se deja pendiente.")
        return None

    store.set(cuit, outcome.item.detail, selected.concept_id)
    return selected.concept_id


def cmd_match(args: argparse.Namespace) -> None:
    source = build_source(args)
    catalog = get_items_catalog_client(settings).get_items()
    store = MatchStore(Path(settings.match_store_path))
    outbox = Path(args.outbox)
    outbox.mkdir(parents=True, exist_ok=True)

    for document in source.fetch_new():
        result = process_document(document)
        if result.errors:
            print(f"[REVISION] {document.filename}: {'; '.join(result.errors)}")
            continue

        print(f"[MATCH] {document.filename} -> {result.service_expense.cuit} / {result.service_expense.number}")
        outcomes = resolve_concepts(result, catalog, store)

        for expense_item, outcome in zip(result.service_expense.items, outcomes):
            if outcome.resolved:
                continue
            new_concept_id = _resolve_interactively(result.service_expense.cuit, outcome, store)
            expense_item.concept_id = new_concept_id

        pending = [item.detail for item in result.service_expense.items if not item.concept_id]
        if pending:
            print(f"    Quedan {len(pending)} linea(s) sin resolver: {', '.join(pending)}")
        else:
            print("    Todas las lineas quedaron resueltas.")
            out_path = outbox / f"{document.filename}.json"
            out_path.write_text(
                json.dumps(result.service_expense.model_dump(by_alias=True, mode="json"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"    Listo para la fase 3, guardado en {out_path}")


def cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn

    from .web import create_app

    app = create_app(inbox_dir=Path(args.path), outbox_dir=Path(args.outbox))
    uvicorn.run(app, host="127.0.0.1", port=args.port)


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Extrae los datos de las facturas, sin resolver items de compra")
    run_parser.add_argument("--source", choices=["manual", "email"], default="manual")
    run_parser.add_argument("--path", default="./inbox")

    match_parser = subparsers.add_parser("match", help="Extrae y ademas resuelve el item de compra de cada linea")
    match_parser.add_argument("--source", choices=["manual", "email"], default="manual")
    match_parser.add_argument("--path", default="./inbox")
    match_parser.add_argument("--outbox", default="./outbox")

    serve_parser = subparsers.add_parser("serve", help="Levanta el panel de revision (fase 2) en el navegador")
    serve_parser.add_argument("--path", default="./inbox")
    serve_parser.add_argument("--outbox", default="./outbox")
    serve_parser.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args)
    elif args.command == "match":
        cmd_match(args)
    elif args.command == "serve":
        cmd_serve(args)


if __name__ == "__main__":
    main()
