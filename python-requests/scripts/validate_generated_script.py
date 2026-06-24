import argparse
import ast
from pathlib import Path
import re
import sys


FORBIDDEN_TEXT = [
    "cdp_debug_url",
    "webSocketDebuggerUrl",
    "127.0.0.1:9222",
    "/json/version",
    "chrome-devtools-mcp",
    "Runtime.evaluate",
]
BANNED_ABSTRACTION_RE = re.compile(r"(helper|client|service|factory|utils?)", re.IGNORECASE)


def fail(message):
    print(f"FAIL: {message}")
    return 1


def validate(path, raw_download, max_classes, max_functions):
    source_path = Path(path)
    text = source_path.read_text(encoding="utf-8")
    lowered_name = source_path.name.lower()

    for token in FORBIDDEN_TEXT:
        if token in text:
            return fail(f"final script contains analysis-only token: {token}")

    if raw_download and "field_mapping" in text:
        return fail("raw download script must not contain field_mapping logic")

    if BANNED_ABSTRACTION_RE.search(lowered_name):
        return fail(f"script filename looks like a generic abstraction: {source_path.name}")

    tree = ast.parse(text, filename=str(source_path))
    classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    functions = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]

    if len(classes) > max_classes:
        return fail(f"too many classes: {len(classes)} > {max_classes}")
    if len(functions) > max_functions:
        return fail(f"too many functions/methods: {len(functions)} > {max_functions}")

    for node in classes + functions:
        if BANNED_ABSTRACTION_RE.search(node.name):
            return fail(f"generic abstraction name is not allowed: {node.name}")

    print("OK: generated script passes python-requests output checks")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Validate generated python-requests scripts.")
    parser.add_argument("script_path")
    parser.add_argument("--raw-download", action="store_true", help="Enforce raw download mode with no field_mapping.")
    parser.add_argument("--max-classes", type=int, default=1)
    parser.add_argument("--max-functions", type=int, default=5)
    args = parser.parse_args()
    return validate(args.script_path, args.raw_download, args.max_classes, args.max_functions)


if __name__ == "__main__":
    sys.exit(main())
