#!/usr/bin/env python3
"""Count body prose in main.tex, the way the course word limit is measured.

Excluded from the count: everything before \\begin{document}, the appendix and
bibliography (both sit after \\bibliographystyle), and every table, figure, and
caption. Only running prose is measured.

    python paper/wordcount.py [main.tex]
"""

import re
import sys

FLOAT_ENVS = [
    "table", "figure", "tabular", "tabularx", "tcolorbox",
    "Verbatim", "verbatim", "tikzpicture", "align", "equation",
]


def strip(text):
    """Reduce LaTeX source to countable prose."""
    text = re.sub(r"(?<!\\)%.*", "", text)
    for env in FLOAT_ENVS:
        text = re.sub(
            r"\\begin\{" + env + r"\*?\}.*?\\end\{" + env + r"\*?\}", " ", text, flags=re.S
        )
    text = re.sub(r"\\caption\{", " ", text)
    return text


def count(text):
    text = re.sub(r"\$[^$]*\$", " X ", text)
    text = re.sub(r"\\url\{[^}]*\}", " X ", text)
    text = re.sub(r"\\(cite\w*|ref|eqref|autoref|label)\{[^}]*\}", " ", text)
    text = re.sub(r"\\[a-zA-Z@]+\*?", " ", text)
    text = re.sub(r"[{}\[\]~&\\]", " ", text)
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’\-\.,%]*", text))


def main(path):
    src = open(path).read()
    body = strip(src.split("\\begin{document}", 1)[1].split("\\bibliographystyle", 1)[0])

    parts = re.split(r"\\section\*?\{([^}]*)\}", body)
    rows = [("(front matter + abstract)", count(parts[0]))]
    rows += [(parts[i], count(parts[i + 1])) for i in range(1, len(parts), 2)]

    width = max(len(name) for name, _ in rows)
    for name, n in rows:
        print(f"{name:{width}s}  {n:>6}")
    print("-" * (width + 8))
    print(f"{'TOTAL body prose':{width}s}  {sum(n for _, n in rows):>6}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "main.tex")
