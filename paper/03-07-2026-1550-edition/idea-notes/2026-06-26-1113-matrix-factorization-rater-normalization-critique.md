# Matrix Factorization Rater Normalization Critique

- **Date:** 2026-06-26 11:13 +0200
- **Source:** Paper discussion

## Context
While explaining the Community Notes algorithm, two terms in the formula stood out
in particular: $i_u$ and $f_u \cdot f_n$. $i_u$ captures the rater's general
tendency toward leniency or strictness, while $f_u \cdot f_n$ captures the
viewpoint alignment between the rater factor and the note factor.

## Idea
These two terms do not directly mean "rater quality" — this should not be stated too
harshly. However, CN's core action, when estimating note quality, is to normalize
by absorbing rater tendencies and viewpoint-match effects into the model. The
critique can be grounded here: rather than placing raters in a quality hierarchy,
we treat distinct behavioral groups as legitimate constituencies and ask whether the
note has crossed the threshold of shared acceptance across those groups.

## Why It Matters
This idea can connect the CN algorithm critique to the CCA philosophy. Later in the
paper it becomes possible to say: while CN attempts to correct rater-level
heterogeneity within a latent model, our approach treats heterogeneity not merely
as a nuisance but as group structure that deserves representation.

Recent work reinforces this connection: Goyal et al. (2026) and Nudo et al. (2026)
argue that quality-estimation structures of this kind can become sensitive to rater
quality, noisy raters, strategic raters, and hyperactive minorities. This point
converges directly with our critique: if the quality estimate relies heavily on the
signal of users whose rating behavior is dense and imbalanced, the influence of the
active minority can grow inside the model. CCA's contribution is to explicitly test
whether distinct constituencies each grant approval, rather than trying to resolve
that influence solely through better rater filtering.

## Follow-up
In the Introduction or methods section, after explaining matrix factorization,
formulate this distinction more carefully. In particular, preserve the separation
between "$i_u$ is not rater quality" and "$f_u \cdot f_n$ is viewpoint
compatibility"; tie the critique to CN's aggregation philosophy, not to a
misreading of these terms. Use the connection to Goyal et al. (2026) and Nudo et
al. (2026) here; specifically link how the weight of active minorities can grow
inside the model to the motivation for CCA.
