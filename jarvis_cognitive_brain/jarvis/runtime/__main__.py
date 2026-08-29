from __future__ import annotations

import argparse
import asyncio
import json

from jarvis.runtime.bootstrap import diagnose, format_status


def main() -> int:
    parser = argparse.ArgumentParser(description="JARVIS local runtime diagnostics")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit machine-readable JSON")
    args = parser.parse_args()

    status = asyncio.run(diagnose())
    if args.as_json:
        print(json.dumps(status.as_dict(), ensure_ascii=False, indent=2))
    else:
        print("JARVIS runtime status")
        print("====================")
        print(format_status(status))
    return 0 if status.ollama_healthy and status.vault_present else 1


if __name__ == "__main__":
    raise SystemExit(main())
