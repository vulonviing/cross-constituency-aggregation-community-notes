# Community Notes Final Presentation V24 — Speaker Notes

Target delivery: **15:15**.

## 1–30. Existing Narrative

Use the delivery associated with V23. These slides are preserved without
changes.

## 31. Same Claim. Different Standard. — 0:45

Begin the results section with one focused case. The note on the left is shown
as Helpful in the study snapshot and makes its factual point using graphic,
provocative language. Representative selection chooses the note on the right,
which states the same core claim more neutrally and with four external sources.
The shown note has cross-constituency support of 73.4 percent; the selected
alternative reaches 79.6 percent and receives a canonical Gemma score of 82.
This does not prove that the shown note is false or that its author intended to
troll. It illustrates how the selection rule can favor a less provocative
formulation.

## 32. What the Platform Shows—and Hides — 0:30

Our Representative strategy selects 44,722 notes. Applying the common CCA
bridge-score threshold of 50 percent retains 20,405, or 46 percent. Of those
qualified picks, Community Notes already shows 6,750 and leaves 13,655 hidden.
The remaining 24,317 picks fall below the CCA threshold. Validation begins with
the 13,655 qualified notes that the platform does not show in the study
snapshot.

## 33. Gemma Validation — 0:40

Validation is separate from aggregation. Gemma Stage 1 requires sourced factual
information with a visible external source pointer. A targeted Stage 1.5 check
reconsiders opinion-labelled notes when they retain a sourced factual core.
Stage 2 scores the admitted notes for rescue-worthiness. Missing sourcing is a
validation failure, not proof that the underlying claim is false.

## 34. A 30.7B Model, Pinned End to End — 0:35

The canonical run used the dense 30.7-billion-parameter Gemma 4 31B instruction
model at one exact revision. It ran locally on SCCKN through vLLM, not through
OpenCode or a hosted API. Each job used two 46-gigabyte NVIDIA L40S GPUs in
tensor-parallel BF16 mode, with thinking enabled and 64 concurrent requests.
The model received one note per independent prompt, without tweet context, URL
fetching, retrieval, embeddings, a vector store, or Gabriel context. Outputs
were generated freely and then checked against a strict JSON schema. Across all
three phases, 25,734 logical judgments consumed 32.1 million model-reported
prompt and completion tokens. Active phase windows totalled about 12 hours and
28 minutes; the first-to-last output window was 15 hours and 51 minutes,
including gaps between phases. The displayed 52-gigabyte peak is an observed
SCCKN scheduler maxvmem figure, not GPU memory consumption.

## 35. From Candidates to Validated Rescues — 0:50

The completed Gemma 4 31B IT run starts from 13,655 hidden CCA candidates.
Stage 2 assigns each admitted note a holistic score from zero to one hundred.
Scores from 90 to 100 indicate a clear, traceable, self-contained note; 70 to 89
indicate strong and useful support. Scores from 40 to 69 contain useful elements
but material gaps, while 10 to 39 indicate limited support or clarity and zero
to nine indicate little usable justification. The display-quality threshold is
50. Gemma validates 8,558 notes, or 62.7 percent of the candidate universe.

## 36. What Makes a Note Worth Rescuing? — 0:35

Rescue-worthiness is a holistic zero-to-one-hundred judgment applied only after
the sourcing and content checks. Gemma evaluates visible source specificity,
claim–source connection, self-contained explanation, neutral language, and
concise constructive presentation. It does not see the original post, open the
URL, or independently verify the source contents.
