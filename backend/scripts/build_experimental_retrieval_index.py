from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any, cast

from app.planes.knowledge.experimental_index import ExperimentalDomain, ExperimentalIndexManager


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build do índice experimental de retrieval do Knowledge Plane.")
    parser.add_argument("--domain", required=True, choices=["docs", "chat", "memory"])
    parser.add_argument("--user-id")
    parser.add_argument("--knowledge-space-id")
    parser.add_argument("--doc-id")
    parser.add_argument("--since-ts", type=int)
    parser.add_argument("--rebuild-full", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json-out")
    return parser


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    manager = ExperimentalIndexManager()
    result = await manager.build_index(
        domain=cast(ExperimentalDomain, args.domain),
        user_id=args.user_id,
        knowledge_space_id=args.knowledge_space_id,
        doc_id=args.doc_id,
        since_ts=args.since_ts,
        rebuild_full=args.rebuild_full,
        dry_run=args.dry_run,
    )
    payload = {
        "dry_run": result.dry_run,
        "output_dir": result.output_dir,
        "manifest": result.manifest.__dict__,
    }
    if args.json_out:
        output_path = Path(args.json_out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    args = _build_parser().parse_args()
    payload = asyncio.run(_run(args))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
