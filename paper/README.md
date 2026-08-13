# paper/

| File | What it is |
|---|---|
| `main.pdf` | **The manuscript.** 18 pages, including the appendices with the frozen validation prompts. |
| `main.tex`, `references.bib`, `main.bbl` | Its source. |
| `conference-abstract-intro/` | The 3-page conference abstract, with its own source and bibliography. |

Build either one with:

```bash
cd paper                          # or paper/conference-abstract-intro
latexmk -pdf main.tex
```

`main.tex` reaches outside this directory twice: for the five figures in
`../figures/script_figures/` and for the three frozen prompt files under
`../data/llm_validation/runs/`, which the appendices quote verbatim. Both build
from a fresh clone with no extra downloads.

To check a number in the paper against the pipeline output that produced it, see
[REPRODUCING.md](../REPRODUCING.md).
