from __future__ import annotations

import argparse
import asyncio
import json

from jarvis.runtime.bootstrap import diagnose, format_status
from jarvis.runtime.chat import ChatRuntime


def main() -> int:
    parser = argparse.ArgumentParser(description="JARVIS local runtime")
    sub = parser.add_subparsers(dest="command")

    status_cmd = sub.add_parser("status", help="Check local runtime readiness")
    status_cmd.add_argument("--json", action="store_true", dest="as_json", help="Emit machine-readable JSON")

    chat_cmd = sub.add_parser("chat", help="Start local conversational runtime")
    chat_cmd.add_argument("--session", default="default", help="Local chat session id")
    chat_cmd.add_argument("--once", help="Send one message and exit")
    chat_cmd.add_argument("--reset", action="store_true", help="Reset the selected local chat session first")
    chat_cmd.add_argument("--stream", action="store_true", help="Stream the Ollama response")

    gui_cmd = sub.add_parser("gui", help="Start the Tkinter desktop runtime")

    args = parser.parse_args()

    if args.command is None:
        args.command = "status"
        args.as_json = False

    if args.command == "status":
        status = asyncio.run(diagnose())
        if args.as_json:
            print(json.dumps(status.as_dict(), ensure_ascii=False, indent=2))
        else:
            print("JARVIS runtime status")
            print("====================")
            print(format_status(status))
        return 0 if status.ollama_healthy and status.vault_present else 1

    if args.command == "gui":
        from jarvis.runtime.gui import main as gui_main
        return gui_main()

    runtime = ChatRuntime(session_id=args.session)
    if args.reset:
        runtime.reset()

    if args.once:
        if args.stream:
            asyncio.run(runtime.stream_reply(args.once))
        else:
            print(f"JARVIS: {asyncio.run(runtime.reply(args.once))}")
        return 0

    print("JARVIS local chat")
    print("Type /exit to quit, /reset to clear the current session.")
    while True:
        try:
            user_text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_text:
            continue
        if user_text.lower() in {"/exit", "/quit"}:
            break
        if user_text.lower() == "/reset":
            runtime.reset()
            print("JARVIS: session reset.")
            continue
        if args.stream:
            asyncio.run(runtime.stream_reply(user_text))
        else:
            print(f"JARVIS: {asyncio.run(runtime.reply(user_text))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
