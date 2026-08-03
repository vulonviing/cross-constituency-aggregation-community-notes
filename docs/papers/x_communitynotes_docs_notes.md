# X Community Notes Docs Notes

This file is a running research memo built from the official Community Notes guide and related X documentation.

## Naming Convention

- `Goyal 2026` = `goyal_2026_quality-sensitive-mf.pdf`
- `Razuvayevskaya 2025` = `razuvayevskaya_2025_timeliness-consensus-crowd.pdf`

## Official Docs Consulted

- Community Notes ranking guide: <https://communitynotes.x.com/guide/en/under-the-hood/ranking-notes>
- X help page on Community Notes: <https://help.x.com/en/using-x/birdwatch>
- Community Notes public repo: <https://github.com/twitter/communitynotes>
- Download-data markdown source: <https://raw.githubusercontent.com/twitter/communitynotes/main/documentation/under-the-hood/download-data.md>
- Open-source code markdown source: <https://raw.githubusercontent.com/twitter/communitynotes/main/documentation/under-the-hood/note-ranking-code.md>

## Key Takeaways So Far

### 1. Official preprocessing is mild, not dense-core extraction

The ranking guide says:

- only raters with at least 10 ratings are included
- only notes with at least 5 ratings are included
- they do not recursively filter until convergence

This is much closer to broad sparse-graph preprocessing than to extracting a tiny dense core.

### 2. `CoreModel` is not the same thing as “political notes”

The official docs define `CoreModel` mainly by modeling population and rollout maturity:

- `CoreModel` covers notes with most ratings from “Core areas” where Community Notes is established
- `ExpansionModel` covers all notes with all ratings across Core and Expansion areas
- `CoverageModel` is a Core-like model with different intercept regularization and thresholding

So the statement in `Goyal 2026` that the “core model” is “notes on political tweets” should be treated cautiously. That appears to be the paper authors’ characterization, not the technical definition given in the official docs.

### 3. Topic assignment is supervised and seed-based, not bare topic modeling

The ranking guide describes a two-phase topic pipeline:

1. Posts with one or more notes are assigned to predefined topics using seed terms.
2. A multiclass logistic regression model is then trained to predict topics and update the assignment.

Important implications:

- this is not free-form unsupervised topic modeling
- X starts from a predefined topic ontology
- text matching plus supervised classification is used to scale topic assignment
- posts can remain unassigned
- posts with multiple seed-term matches are initially unassigned

This is likely why X can do topic-specific modeling without the kind of bottleneck that arises when one tries to discover political topics from scratch using generic topic models.

### 4. Topic models are separate from the main Core model

The guide distinguishes:

- `CoreModel`
- `ExpansionModel`
- `CoverageModel`
- `CoreWithTopics`
- topic-specific models

The docs say that `CoreWithTopics` includes all notes assigned to a topic, and that final status for those notes is then combined with `TopicModels`.

This suggests that topic assignment may matter for a subset of notes, but it is not the same thing as the platform’s entire main ranking pipeline.

### 5. The docs expose a potentially useful data hook

The ranking guide changelog says that on March 13, 2023 X released:

- “a new `modelingPopulation` column in the user enrollment file, which indicates whether a user is included in the core or expansion model”

This may be extremely useful for sample construction if that column is available in the downloadable public data.

### 6. The ranking guide changelog reveals public data additions

Two changelog entries from the official ranking guide are especially important:

- July 13, 2022: X says it released a new `note status history` dataset
- March 13, 2023: X says it released a new `modelingPopulation` column in the user enrollment file

These are useful because they suggest that some of the sample-construction logic may be reproducible from public artifacts without running our own topic model first.

### 7. The official docs are backed by the public GitHub repo

The `twitter/communitynotes` repository states that:

- `/documentation` is the source of truth for the markdown used to generate `communitynotes.x.com/guide`
- `/scoring/src` contains the open-source scoring code
- the production scorer can be reproduced locally by downloading the public data and running `python main.py`

This matters because when website routes are hard to discover, we can read the exact markdown source directly from GitHub.

### 8. The public daily download has five normalized tables

According to `download-data.md`, the public download contains five cumulative files:

- `Notes`
- `Ratings`
- `Note Status History`
- `User Enrollment`
- `Note Requests`

The docs explicitly say these are normalized tables and that note-related tables can be joined by `noteId`.

### 9. The public download already exposes model-assignment metadata

The `User Enrollment` schema documents:

- `modelingPopulation`: `"CORE"` or `"EXPANSION"`
- `modelingGroup`: group-model ID

The `Note Status History` schema documents:

- `currentCoreStatus`
- `currentExpansionStatus`
- `currentGroupStatus`
- `currentMultiGroupStatus`
- `currentDecidedByKey`
- `currentModelingGroup`
- `currentModelingMultiGroup`

This is very important for sample construction because it means we can likely identify which model family scored a note, and which contributor population a user belongs to, without topic modeling from scratch.

### 10. Topic assignment does not appear to be a raw public-download field

From the raw public data documentation, I do **not** currently see a direct topic label field in the five daily download tables.

However, the open-source scoring code does define topic-related output columns such as:

- `noteTopic`
- `topicNoteIntercept`
- `topicRatingStatus`
- `coreWithTopicsNoteIntercept`

This suggests a distinction:

- raw daily public download: likely no direct topic assignment column
- reproduced scorer output (`scoredNotes.tsv`): topic-related fields may become available after running the open-source scorer locally

So if we want X-style topic assignments, we may need to run the scoring pipeline ourselves rather than expect the raw daily files to hand us a topic label directly.

### 11. The official topic model code confirms the seed-term plus supervised approach

The public `topic_model.py` starts with the description:

- assign notes to a predetermined set of topics
- seed with a small set of indicative terms
- expand assignment using logistic regression on bag-of-words features
- exclude tokens containing seed terms from the logistic-regression features

The visible seed topics in the current code include:

- `UkraineConflict`
- `GazaConflict`
- `MessiRonaldo`
- `Scams`
- `InDimensionTwo`

This reinforces that X is not using free-form topic discovery here.

## Quotes / Paraphrases Worth Reusing

### Pre-filtering

Official guide summary:

- pre-filter to raters with at least 10 ratings
- pre-filter to notes with at least 5 ratings

### Topic modeling

Official guide summary:

- topic assignment first uses predefined seed terms
- then trains a multiclass logistic regression model
- topic models run on notes and ratings assigned to each topic

### Multi-model ranking

Official guide summary:

- `CoreModel` is about established “Core areas”
- `ExpansionModel` includes all notes and ratings across Core and Expansion areas
- `CoverageModel` modifies Core-style ranking to increase helpful coverage

### Public data hooks from changelog

Official guide summary:

- `note status history` was added to the public download in July 2022
- `modelingPopulation` was added to the user enrollment file in March 2023
- the `modelingPopulation` field indicates whether a user is included in the Core or Expansion model

### Public schema we can likely exploit immediately

Official `download-data.md` summary:

- public data is released as `Notes`, `Ratings`, `Note Status History`, `User Enrollment`, and `Note Requests`
- `User Enrollment` includes `modelingPopulation` and `modelingGroup`
- `Note Status History` includes submodel-specific statuses and `currentDecidedByKey`

### Reproducible scorer outputs

Official `note-ranking-code.md` summary:

- downloading the public data and running `python main.py` produces `scoredNotes.tsv`
- that reproduced output should match production scoring for the corresponding snapshot, up to timing subtleties between prescoring and final scoring

### Topic-related internal output fields

Open-source scoring constants define output keys including:

- `noteTopic`
- `topicNoteIntercept`
- `topicRatingStatus`
- `coreWithTopicsNoteIntercept`

This suggests topic information is available in scorer output even if it is not directly present in the raw download tables.

### Valid ratings window

Official guide summary from the July 13, 2022 changelog:

- valid ratings are no longer just the first 5 ratings
- ratings are valid if they occur within 48 hours after note creation and before the note first receives Helpful or Not Helpful status
- if status flips between Helpful and Not Helpful, ratings remain valid until that flip

## Why This Matters For Our Project

### Immediate methodological implication

If our student is using bare topic models just to identify political notes, that is probably the wrong bottleneck. The official X system appears to avoid that by using:

- predefined topics
- seed-term labeling
- supervised topic classification
- model-assignment metadata

### Likely better strategy

Instead of starting with unsupervised topic modeling over all notes:

1. check whether public data exposes model-assignment or topic-related metadata
2. check whether user-level `modelingPopulation` is available
3. use `Note Status History` and `User Enrollment` to recover model-family assignment where possible
4. if needed, reproduce `scoredNotes.tsv` locally using the open-source scorer
5. only build our own classifier if the relevant metadata are still unavailable

## Next Docs To Pull

- any public schema or file descriptions for:
  - user enrollment
  - note status history
  - ratings
  - note metadata
- any documentation showing exactly how `currentDecidedByKey` values map to scorer families over time
- any public examples or code paths showing how `noteTopic` enters `scoredNotes.tsv`
- any practical guidance on reproducing `scoredNotes.tsv` from a snapshot in our environment

## Access Notes

- The official ranking guide page is accessible and currently the most informative source.
- Direct requests to likely `Downloading data` and `Open-source code` English guide URLs returned 404 during this session, but the corresponding markdown source is directly accessible in the public GitHub repo under `documentation/under-the-hood/`.

## Current Best Read

At this point, the strongest interpretation is:

- X’s raw public data already exposes enough metadata to broaden the sample without first running an unsupervised topic model
- `modelingPopulation` and model-decision fields are directly public
- topic labels may not be directly present in the raw download, but topic-related outputs appear available after reproducing the scorer locally

That means the student’s current bottleneck may be partly self-imposed: bare topic modeling is probably not the first thing to do if the immediate goal is sample construction.

## Open Questions

- Does the public download currently expose `modelingPopulation`?
- Does any public file expose topic assignment directly?
- Did `Goyal 2026` actually use a public field for sample construction, or did they impose an additional private classification step?
- Is there a practical way for us to reproduce “topic” or “core-with-topics” sample logic from public artifacts alone?
