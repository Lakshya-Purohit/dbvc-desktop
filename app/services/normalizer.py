"""SQL normalization via sqlparse."""

import sqlparse


def normalize(sql: str) -> str:
    """Normalize SQL for consistent comparison."""
    return sqlparse.format(
        sql,
        keyword_case="upper",
        strip_comments=True,
        reindent=True,
    )
