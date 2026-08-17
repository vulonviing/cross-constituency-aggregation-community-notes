# paper/

| File | What it is |
|---|---|
| `Ulu_Yao.pdf` | **The manuscript.** 16 pages; main body ~7,500 words, within the 8,000-word course limit. |
| `main.tex`, `references.bib`, `main.bbl` | Its source. |
| `wordcount.py` | Counts the main body: prose, then prose plus tables and figures. Appendix and bibliography are excluded, since the word limit is on the main body. Run it as `python wordcount.py main.tex`. |
| `pdfwordcount.sh` | The same count taken off the built PDF, title to References, the way a plain word counter sees it. Run it as `./pdfwordcount.sh main.pdf`. |
| `long-version/` | The manuscript as first submitted, before it was shortened: `main_long.tex` and `Ulu_Yao_long.pdf`. |

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
`../data/llm_validation/runs/`, which the appendix quotes verbatim. Both
resolve in a fresh clone with no extra downloads. The same three prompts are
also collected, with their hashes, at
[`../data/llm_validation/PROMPTS.md`](../data/llm_validation/PROMPTS.md).

To check a number in the paper against the pipeline output that produced it, see
[REPRODUCING.md](../REPRODUCING.md).
