# Community Notes Final Presentation V2 — Speaker Notes

Target delivery: **9:20**, leaving roughly 40 seconds of buffer.

## 1. Who Speaks for the Crowd? — 0:15

Community Notes asks a crowd which context deserves public visibility. Our
question is whether the current aggregation rule allows that whole crowd to
speak.

## 2. One Note. One Decision. — 0:50

Start with one user. They encounter a post, read the attached context, and rate
whether the note is helpful. That small action contributes to a public decision:
whether the note appears below the post.

## 3. Now Multiply That by Thousands — 0:50

The same action is repeated by thousands of contributors. Community Notes must
turn these scattered ratings into one visibility decision. This is the central
aggregation task.

## 4. But the Crowd Is Not Equal — 1:05

Participation is not evenly distributed. Most people rate occasionally, while
a small group rates constantly. In our 200k analysis, a 64-user outlier rated
around eleven times more often than the main camps. A crowd can therefore be
large without every participant having an equal influence on the observed
record.

## 5. The Map Inherits the Imbalance — 1:10

Community Notes uses rating patterns to infer a latent viewpoint map, then asks
whether support crosses that map. Bridging is a sensible objective, but the map
itself is partly drawn by whoever rates most often. Unequal activity can
therefore shape which agreement the model interprets as cross-group support.

## 6. Consult Constituencies Directly — 0:55

Our alternative changes the unit of aggregation. We recover behaviorally
distinct constituencies, measure approval inside each one, and combine those
signals explicitly. Similar design intuitions appear in divided societies,
where important decisions may require support across regions or communities.

## 7. Four Design Principles — 0:55

Every constituency should enter the decision. Enthusiasm in one group should
not erase rejection in another. The same rule should apply to all groups, and
the groups should be recovered from rating behavior rather than imposed through
political or demographic labels.

## 8. Principles Become Operations — 1:25

Each principle has a direct operational counterpart. A note needs at least
three ratings from every constituency. Approval rates enter a geometric mean,
which creates a soft veto: ninety percent support in one group and ten percent
in the other produces thirty percent, not fifty percent. We apply this rule to
the 100k-note, 200k-rater analytical slice and validate rescue candidates
separately with Gabriel.

## 9. From Hidden to Validated — 1:15

Community Notes shows 6,832 of the 44,722 Representative-picked notes, or 15
percent. Cross-constituency aggregation identifies 13,655 additional candidates,
raising potential visibility to 46 percent before validation. We do not claim
that every candidate should appear: Gabriel classifies 3,896 as sourced,
factual, and rescue-worthy.

## 10. An Aggregation Problem — 0:40

Bridging is the right ambition. Cross-constituency aggregation makes that
ambition explicit: recover the constituencies, require support across them, and
validate content separately. Community Notes is not only a prediction problem;
it is an aggregation problem.
