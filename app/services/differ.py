"""
Diff computation — unified diffs for SQL objects.
"""

import difflib
from app.logger import get_logger

log = get_logger("differ")


def generate_diff(sql1: str, sql2: str, label1: str = "Source", label2: str = "Target") -> list[str]:
    """Generate a unified diff between two SQL strings."""
    lines = list(difflib.unified_diff(
        sql1.splitlines(),
        sql2.splitlines(),
        fromfile=label1,
        tofile=label2,
        lineterm="",
    ))
    log.debug("Diff generated: %d diff lines", len(lines))
    return lines


def compute_line_diffs(source_lines: list[str], target_lines: list[str]) -> list[dict]:
    """
    Compute line-by-line diffs for a side-by-side viewer.

    Returns a list of dicts:
        {
            "left_line": str | None,
            "right_line": str | None,
            "left_num": int | None,
            "right_num": int | None,
            "status": "equal" | "added" | "removed" | "modified"
        }
    """
    matcher = difflib.SequenceMatcher(None, source_lines, target_lines)
    result = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for i, j in zip(range(i1, i2), range(j1, j2)):
                result.append({
                    "left_line": source_lines[i],
                    "right_line": target_lines[j],
                    "left_num": i + 1,
                    "right_num": j + 1,
                    "status": "equal",
                })

        elif tag == "replace":
            max_len = max(i2 - i1, j2 - j1)
            for k in range(max_len):
                left = source_lines[i1 + k] if (i1 + k) < i2 else None
                right = target_lines[j1 + k] if (j1 + k) < j2 else None
                result.append({
                    "left_line": left,
                    "right_line": right,
                    "left_num": (i1 + k + 1) if left is not None else None,
                    "right_num": (j1 + k + 1) if right is not None else None,
                    "status": "modified",
                })

        elif tag == "delete":
            for i in range(i1, i2):
                result.append({
                    "left_line": source_lines[i],
                    "right_line": None,
                    "left_num": i + 1,
                    "right_num": None,
                    "status": "removed",
                })

        elif tag == "insert":
            for j in range(j1, j2):
                result.append({
                    "left_line": None,
                    "right_line": target_lines[j],
                    "left_num": None,
                    "right_num": j + 1,
                    "status": "added",
                })

    return result
