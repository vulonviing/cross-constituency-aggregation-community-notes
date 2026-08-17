# paper/

| File | What it is |
|---|---|
| `Ulu_Yao.pdf` | **The manuscript.** 18 pages, including the appendices with the frozen validation prompts. |
| `main.tex`, `references.bib`, `main.bbl` | Its source. |

Build it with:

```bash
cd paper
latexmk -pdf main.tex
mv main.pdf Ulu_Yao.pdf
```

`latexmk` names its output after the source, so the build produces `main.pdf`;
the committed copy carries the authors' names for submission.

`main.tex` reaches outside this directory twice: for the five figures in
`../figures/script_figures/` and for the three frozen prompt files under
`../data/llm_validation/runs/`, which the appendices quote verbatim. Both
resolve in a fresh clone with no extra downloads.

To check a number in the paper against the pipeline output that produced it, see
[REPRODUCING.md](../REPRODUCING.md).
