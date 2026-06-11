_SPECIAL_CHARS: dict[str, str] = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def escape(text: str) -> str:
    """Escape special LaTeX characters in plain text strings."""
    result: list[str] = []
    for ch in text:
        result.append(_SPECIAL_CHARS.get(ch, ch))
    return "".join(result)
