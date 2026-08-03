# Community Notes Final Presentation V8 — Speaker Notes

Target delivery: **11:35**.

## 1. Who Speaks for the Crowd? — 0:15

Community Notes asks a crowd which context deserves public visibility. Our
question is whether the current aggregation rule allows that whole crowd to
speak.

## 2–5. One Note. One Decision. — 1:20 total

Start with one user. They encounter a post, read the attached Community Note,
and choose whether the context is helpful. The progressive reveals show the
same action becoming an input to a public visibility decision.

## 6. Now Multiply That by Thousands — 0:45

Thousands of contributors repeat the same action. The platform must aggregate
these scattered ratings into one visibility outcome.

## 7–11. Core Problem 1: It Reads the Rater — 0:55 total

Predictable partisan approval can be absorbed by viewpoint compatibility,
while agreement between raters placed on opposing sides raises the note
intercept. The system therefore interprets who voted and whether the vote was
expected instead of consulting constituencies through explicit approval rates.

## 12–15. Core Problem 2: The Same Hands Draw the Map — 0:55 total

The viewpoint map is learned from an unequal rating record. Like a teacher who
keeps hearing from the same students, the system can mistake an active core for
the whole class. In our 200k analysis, a 64-user outlier rated around eleven
times more often than the main camps.

## 16–19. The Handshake Is Right. The Electorate Is Not. — 0:35 total

Enemies Shaking Hands is a good intuition. But the opportunity to observe such
agreement depends on who enters the rating record. Balanced participation gives
a fifty-percent cross-group encounter rate; at ninety–ten, it falls to eighteen
percent. Partisan compatibility then changes how clicks are credited, while
activity determines who represents each side.

## 20. This Problem Predates Platforms — 0:35

Divided societies have long required decisions to travel across groups.
Switzerland uses a double majority; Belgium uses parallel linguistic consent;
Bosnia protects constituent peoples with vital-interest vetoes; and Northern
Ireland requires cross-community support. The shared principle is that no group
decides alone.

## 21–22. From Ratings to Constituencies — 0:35 total

We compare users through their patterns on overlapping notes—not outside
labels. Spectral clustering recovers the constituencies, and Method B reassigns
small outlier groups using correlation with the main camps’ note-level vote
profiles.

## 23. Consult Constituencies Directly — 0:45

Our alternative measures approval inside behaviorally recovered constituencies
and combines those signals explicitly, without allowing one group to stand in
for the whole crowd.

## 24. Four Design Principles — 0:45

Every constituency should be present. One group should not compensate for
another’s rejection. The same rule should apply symmetrically, and groups should
be recovered from behavior rather than outside labels.

## 25. P1 — Presence — 0:25

We begin with coverage. This note has ninety ratings from constituency A but
only two from constituency B. Total volume is not enough: until every recovered
constituency contributes at least three ratings, we do not score the note.

## 26. P2 — Non-compensation — 0:25

Once B reaches ten ratings, the pooled count looks excellent: eighty-one
Helpful votes in A plus one in B produce eighty-two percent overall, so a simple
pooled threshold passes the note. CCA asks a different question. The geometric
mean of ninety and ten percent is thirty percent, below the fifty-percent
threshold. One constituency’s enthusiasm cannot erase another’s rejection.

## 27. P3 — Symmetry — 0:25

The groups enter the rule symmetrically. Ninety raters do not give constituency
A nine times the weight of a ten-rater constituency. Swapping A and B leaves the
geometric mean unchanged: the rule listens to each constituency in the same
way.

## 28. P4 — Behavioral Recovery — 0:25

We do not import party, country, or ideology labels. The two constituencies are
recovered from co-rating behavior among 200,000 active raters. Method B then
reassigns small outlier groups according to their note-level vote-profile
correlation with the two main camps.

## 29. From Hidden to Validated — 1:05

Community Notes shows 6,832 of the 44,722 Representative-picked notes. CCA
identifies 13,655 additional candidates, raising potential visibility to 46
percent before validation. Gabriel classifies 3,896 as sourced, factual, and
rescue-worthy.

## 30. An Aggregation Problem — 0:40

Bridging is the right ambition. Cross-constituency aggregation makes that
ambition explicit: recover the constituencies, require support across them, and
validate content separately.
