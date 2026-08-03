# Community Notes Final Presentation — Speaker Notes

Target delivery: **9:15**, leaving roughly 45 seconds of buffer.

## 1. Who Speaks for the Crowd? — 0:15

Community Notes asks a crowd which context deserves public visibility. Our
question is whether the current aggregation rule allows the whole crowd to
speak.

## 2. What Is Community Notes? — 0:45

A contributor adds context to a post, and other contributors rate whether that
context is helpful. This is not a normal like count: the platform must decide
whether the observed support is broad enough to make the note publicly visible.

## 3. Not Just Majority Rule — 0:50

Bridging is the strongest part of the current design. The system tries to reward
notes that appeal across viewpoints rather than notes backed by only one
faction. The difficulty is how it decides that a bridge exists.

## 4. The Bridge Is Indirect — 1:15

The model estimates whether a rating was predictable from the rater rather than
measuring explicit approval inside each community. Sparse and unequal
participation then matters because highly active raters help define the latent
map itself. In our 200k analysis, a 64-user outlier rated around eleven times
more often than the main camps.

## 5. Consult Constituencies Directly — 0:55

We change the unit of aggregation. Divided societies offer a useful design
analogy: in Switzerland, total support alone may be insufficient because
regional support also matters. We borrow that aggregation intuition, not the
political institution itself.

## 6. Four Design Principles — 0:55

The rule should include every constituency, prevent one group from fully
compensating for another group's rejection, treat groups symmetrically, and
recover them from behavior rather than external political or demographic
labels.

## 7. Principles Become Operations — 1:25

Each principle has an operational counterpart. A note needs at least three
ratings from every constituency. Approval rates enter a geometric mean, which
acts as a soft veto. For example, ninety percent support in one group and ten
percent in the other produces a score of thirty percent, not fifty percent.
The groups themselves come from the co-rating patterns of 200,000 raters, with
Method-B reassignment for outliers.

## 8. What We Tested — 0:55

The analytical slice contains 100,000 notes and 200,000 raters. After recovering
two behavioral constituencies, we select one Representative note for each post.
A hidden note scoring above 0.5 enters the rescue pool. Gabriel validation is
separate, so cross-group support and content quality are not collapsed into the
same judgment.

## 9. Candidates, Then Validation — 1:25

Community Notes shows 6,832 of the 44,722 Representative-picked notes, or 15
percent. Cross-constituency aggregation identifies 13,655 additional candidates,
raising potential pre-validation visibility to 46 percent. We do not claim that
all candidates should be displayed: Gabriel classifies 3,896 as sourced,
factual, and rescue-worthy. The main limitations are the two-camp assumption and
the use of model-based content validation.

## 10. Takeaway — 0:35

Bridging is the right ambition. Cross-constituency aggregation makes that
ambition explicit and inspectable: recover the constituencies, require support
across them, and validate content separately. Community Notes is not only a
prediction problem; it is an aggregation problem.
