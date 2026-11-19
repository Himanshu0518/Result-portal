"""
File decoding utilities.

Steps:
1. Check for null bytes (binary file).
2. Try utf-8-sig (handles BOM). If that fails, try cp1252 and set encoding_note.
3. Return (text, encoding_note).
"""
from __future__ import annotations


MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def decode_file(raw_bytes: bytes, filename: str) -> tuple[str, str | None]:
    """
    Decode raw bytes to a text string.

    Returns:
        (text, encoding_note)
        encoding_note is None if utf-8-sig succeeded, or a string like
        "guessed cp1252" if the fallback was used.

    Raises:
        ValueError with a plain-English message for file-level errors.
    """
    if len(raw_bytes) == 0:
        raise ValueError("The uploaded file is empty.")

    if len(raw_bytes) > MAX_FILE_SIZE:
        raise ValueError(
            f"File exceeds the 10 MB size limit ({len(raw_bytes) / 1_048_576:.1f} MB)."
        )

    if b"\x00" in raw_bytes:
        raise ValueError("This does not look like a CSV file (binary/null bytes detected).")

    if not filename.lower().endswith(".csv"):
        raise ValueError(
            f"Only .csv files are accepted; received '{filename}'."
        )

    # Try UTF-8 with BOM first.
    try:
        text = raw_bytes.decode("utf-8-sig")
        return text, None
    except UnicodeDecodeError:
        pass

    # Fall back to cp1252 (common for Excel exports).
    try:
        text = raw_bytes.decode("cp1252")
        return text, "guessed cp1252"
    except UnicodeDecodeError:
        pass

    raise ValueError(
        "File could not be decoded as UTF-8 or cp1252. "
        "Please save the file as UTF-8 and try again."
    )
