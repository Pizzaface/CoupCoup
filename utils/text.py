import re


def clean_text(text: str) -> str | None:
    if not text:
        return None

    # Remove special characters, except for a few
    return re.sub(
        r"[^a-zA-Z\u00C0-\u00ff\s |$#!%&*(),':.\[\]?\\/\"><+_\-0-9]", '', text
    )
