# Community Notes Final Presentation V7 — Speaker Notes

Target delivery: **11:05**.

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

The model does not evaluate every Helpful click in the same way. Predictable
partisan approval can be absorbed by viewpoint compatibility, while agreement
between raters placed on opposing sides raises the note intercept. The system
therefore interprets who voted and whether the vote was expected instead of
consulting constituencies through explicit approval quantities.

## 12–15. Core Problem 2: The Same Hands Draw the Map — 0:55 total

The viewpoint map is learned from an unequal rating record. Like a teacher who
keeps hearing from the same students, the system can mistake an active core for
the whole class. In our 200k analysis, a 64-user outlier rated around eleven
times more often than the main camps.

## 16. The Handshake Is Right. The Electorate Is Not. — 0:35

Enemies Shaking Hands is actually a good intuition. If two groups that usually
disagree both endorse the same note, that agreement is valuable. But the
opportunity to observe such a handshake depends on who enters the rating
record. With balanced participation, a random encounter crosses groups half the
time. At ninety–ten, that falls to eighteen percent. Then two further problems
enter: partisan compatibility changes how the same click is credited, while
activity determines who draws and represents each side. So we keep cross-group
consent, but make representation explicit.

## 17. This Problem Predates Platforms — 0:35

Long before online platforms, divided societies faced the same collective-
decision problem. Switzerland requires both a popular and cantonal majority;
Belgium uses parallel linguistic consent; Bosnia protects constituent peoples
with vital-interest vetoes; and Northern Ireland requires cross-community
support for key votes. The shared principle is that no group decides alone. We
borrow that design intuition, not the constitutional machinery.

## 18. From Ratings to Constituencies — 0:35

Each row is a rater and each column is a note. We compare users through their
patterns on overlapping notes—not through outside labels. Each user is connected
to their closest behavioral neighbors, spectral clustering recovers the
constituencies, and Method B reassigns small outlier groups using correlation
with the main camps’ note-level vote profiles.

## 19. Consult Constituencies Directly — 0:45

Our alternative recovers behaviorally distinct constituencies, measures
approval inside each one, and combines those signals explicitly. We recover the
groups, consult each group, and aggregate without allowing one group to stand in
for the whole crowd.

## 20. Four Design Principles — 0:45

Every constituency should enter the decision. Enthusiasm in one group should
not erase rejection in another. The same rule should apply to all groups, and
the groups should be recovered from behavior rather than external labels.

## 21. Principles Become Operations — 1:10

A note needs at least three ratings from every constituency. Approval rates
enter a geometric mean, the groups are treated symmetrically, and Method B
recovers the two production constituencies from the 200k-rater pipeline.

## 22. From Hidden to Validated — 1:05

Community Notes shows 6,832 of the 44,722 Representative-picked notes. CCA
identifies 13,655 additional candidates, raising potential visibility to 46
percent before validation. Gabriel classifies 3,896 as sourced, factual, and
rescue-worthy.

## 23. An Aggregation Problem — 0:40

Bridging is the right ambition. Cross-constituency aggregation makes that
ambition explicit: recover the constituencies, require support across them, and
validate content separately.
