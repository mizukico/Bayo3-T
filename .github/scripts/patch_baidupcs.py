#!/usr/bin/env python3
"""Apply the narrowly scoped BaiduPCS-Go v4.0.2 upload preflight workaround."""
from pathlib import Path
import sys

root = Path(sys.argv[1])
path = root / "baidupcs" / "prepare.go"
source = path.read_text(encoding="utf-8")

def replace_once(old: str, new: str, label: str) -> None:
    global source
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    source = source.replace(old, new, 1)

replace_once(
    """\tpcsError = pcs.CheckIsdir(OperationRapidUpload, targetPath, policy, length)
\tif pcsError != nil {
\t\treturn nil, pcsError
\t}
""",
    """\t// Skip the separate Isdir preflight; the precreate endpoint validates the target.
""",
    "Fake upload preflight",
)
replace_once(
    """\tpcsError = pcs.CheckIsdir(OperationRapidUpload, targetPath, policy, totalSize)
\tif pcsError != nil {
\t\treturn nil, pcsError
\t}
""",
    """\t// Skip the separate Isdir preflight; the precreate endpoint validates the target.
""",
    "Rapid upload preflight",
)
path.write_text(source, encoding="utf-8")
print("Patched both upload preflight checks.")
