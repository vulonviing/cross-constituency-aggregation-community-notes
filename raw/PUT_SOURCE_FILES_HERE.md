# Raw Inputs

Place these local-only files in this directory:

- `notes-*.tsv`
- `ratings-*.tsv`
- `noteStatusHistory-00000.tsv`
- `lid.176.ftz`
- executable FastText CLI binary named `fasttext`

Official Community Notes data:

- <https://x.com/i/communitynotes/download-data>
- <https://communitynotes.x.com/guide/en/under-the-hood/download-data>

FastText language model:

- <https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz>

Verify from the repository root:

```bash
ls -lh raw/
test -x raw/fasttext
```

On SCCKN, keep the repository and raw data under `/work`; the home directory
quota is too small for the snapshot.
