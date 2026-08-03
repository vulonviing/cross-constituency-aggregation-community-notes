# Participation Inequality and Clustering Limit

- **Date:** 2026-06-26 11:18 +0200
- **Source:** Paper discussion

## Context
Razuvayevskaya et al. (2025) report that participation in Community Notes is
highly unequal: the top 10% of contributors produce 58% of all notes, while
most users remain much less active. This should not stay only as an external
literature point in the introduction.

## Idea
We also observe the practical consequences of participation inequality in our
own clustering work. In the archived scale-up experiments, increasing the
sample size eventually created serious clustering problems. The 200k-user /
100k-note matrix became the production choice because it was the largest clean
setting with balanced final camps and enough note-level density. Larger
variants started to show reliability and interpretability costs, and the 250k
initial run became degenerate, separating 249,933 users from only 67 users.

This means our empirical pipeline partly rediscovers and confirms the same
structural issue: Community Notes formally contains many contributors, but
usable cross-rater structure is dominated by uneven participation and a small
high-activity core.

## Why It Matters
This can strengthen the data and findings sections. The paper can say that
participation inequality is not only a background fact from prior work; it also
appears in our own methodological diagnostics. The choice to stop at the 200k /
100k matrix is therefore not arbitrary. It is a response to the same imbalance
that motivates the paper: beyond a certain scale, adding more users does not
automatically add representative structure, because sparse and unequal
participation can produce tiny outlier clusters or unstable constituency
interpretations.

## Follow-up
Use this idea in the data/methods section when explaining the dense-core sample
and in the findings/appendix discussion when justifying the 200k-user /
100k-note production matrix. Connect Razuvayevskaya et al. (2025) to our
archived scale-up diagnostics: prior work shows participation inequality at
the platform level; our clustering attempts show how that inequality becomes a
technical constraint for constituency recovery.
