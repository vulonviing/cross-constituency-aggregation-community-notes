# Community Notes Final Presentation V4 — Speaker Notes

Target delivery: **9:20**, leaving roughly 40 seconds of buffer.

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

## 7. Core Problem 1: It Reads the Rater — 0:55

The model does not evaluate every Helpful click in the same way. When an
ideologically aligned rater supports a matching note, viewpoint compatibility
can explain that approval, so the note receives little additional credit. When
raters placed on opposing sides support the same note, their agreement is
surprising under the model and the note intercept rises. The criticism is that
the system interprets who voted and whether that vote was predictable rather
than consulting communities through explicit approval quantities.

## 8. Core Problem 2: The Same Hands Draw the Map — 0:55

The previous mechanism assumes that the viewpoint map is an honest picture of
the crowd. It is learned from the rating record, however, and participation is
highly unequal. Like a teacher who repeatedly hears from the same few students,
the system can mistake an active core for the class. In our 200k analysis, a
64-user outlier rated around eleven times more often than the main camps.

## 9. Consult Constituencies Directly — 0:45

Our alternative recovers behaviorally distinct constituencies, measures
approval inside each one, and combines those signals explicitly. Similar design
intuitions appear in systems that require support across regions or communities.

## 10. Four Design Principles — 0:45

Every constituency should enter the decision. Enthusiasm in one group should
not erase rejection in another. The same rule should apply to all groups, and
the groups should be recovered from behavior rather than external labels.

## 11. Principles Become Operations — 1:10

A note needs at least three ratings from every constituency. Approval rates
enter a geometric mean, the groups are treated symmetrically, and Method B
recovers the two production constituencies from the 200k-rater pipeline.

## 12. From Hidden to Validated — 1:05

Community Notes shows 6,832 of the 44,722 Representative-picked notes. CCA
identifies 13,655 additional candidates, raising potential visibility to 46
percent before validation. Gabriel classifies 3,896 as sourced, factual, and
rescue-worthy.

## 13. An Aggregation Problem — 0:40

Bridging is the right ambition. Cross-constituency aggregation makes that
ambition explicit: recover the constituencies, require support across them, and
validate content separately.
