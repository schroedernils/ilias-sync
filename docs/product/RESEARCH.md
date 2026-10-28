# Research foundation

Reviewed 27 October 2026. This is a targeted literature and product-documentation review, not a systematic review, meta-analysis or study of IliasSync users.

## Questions and evidence discipline

The search followed six questions: how to remove checking/remembering work; how to calibrate trust in incomplete automation; how people re-find personal information; what interruptions cost; which access problems occur in higher education; and how to measure outcomes without surveillance. Searches combined these concepts with original authors, CHI/SIGIR/Human Factors publications, university repositories and official product documentation. Older foundational work was checked against newer findings where available.

**E** means empirical evidence in the source, **S** a research synthesis or framework, **C** an established convention or documented product behavior, **H** an IliasSync hypothesis, and **X** an exploratory idea. An implication is a proposed transfer, not a finding about this app. Statistical association is not causation. A large survey is not automatically representative.

Primary records and author-hosted papers were preferred. Access depth is recorded below. Some publisher full-text requests failed; accessible abstracts and indexed publisher passages support narrower conclusions. No claim depends on a full paper that was unavailable. Sources' web crawl dates were not treated as publication dates. The 2024/25 Jisc survey is a dated dataset, not a claim to be the newest report.

## R1 — Offload the intention to check

[Risko & Gilbert, Cognitive Offloading, 2016, Trends in Cognitive Sciences](https://doi.org/10.1016/j.tics.2016.07.002). **S**; publisher abstract and summary accessed; full-text request denied. A conceptual review connects external actions with reduced internal processing demand and metacognitive choices. It supplies a mechanism, not a measured benefit for file synchronization. **H:** retain a trustworthy account of changes so students need not remember which course they last checked. Validate reduced checking burden; do not promise better grades or working-memory gains.

[Gilbert, Strategic use of reminders, 2015, Consciousness and Cognition](https://samgilbert.net/pubs/Gilbert2015ConsciousnessCognition.pdf). **E**; author-hosted full text, methods and abstract inspected. Web experiments (Experiment 1 N=400; Experiment 2 N=303) relate reminder choice to both confidence and objective ability; reminders improved the task. The task uses delayed intentions involving circles, not real academic files. **H:** measure whether status is understood, not merely whether students feel reassured. Confidence alone cannot establish appropriate reliance.

## R2 — Assistance has its own effort cost

[Chiu & Gilbert, Influence of the physical effort of reminder-setting on strategic offloading of delayed intentions, 2024 issue; online 2023](https://doi.org/10.1177/17470218231199977). **E**; open full text, abstract and Experiment 1 methods inspected. Two preregistered experiments manipulate reminder-setting effort; more effort reduces reminder use. Experiment 1's final sample is 52 online participants. Motor effort in a constrained task is not equivalent to interface configuration. **H:** a changes workflow should not require classifying every document or clearing an obligatory inbox. Compare net work, including acknowledgement effort, rather than clicks alone.

## R3 — Appropriate reliance is more useful than maximum trust

[Lee & See, Trust in Automation: Designing for Appropriate Reliance, 2004, Human Factors](https://doi.org/10.1518/hfes.46.1.50_30392). **S**; publisher abstract and author-paper indexed passages accessed; direct full-text access failed. This multidisciplinary review models how context, automation characteristics and trust influence reliance. It is not an experiment proving that one status design works. **H:** expose the age and scope of completed checks, retain failure evidence, and avoid certainty beyond what the crawler established. Test false confidence using intentionally incomplete scenarios.

## R4 — Search and contextual navigation solve different retrieval problems

[Teevan, Alvarado, Ackerman & Karger, The Perfect Search Engine Is Not Enough, CHI 2004](https://people.csail.mit.edu/teevan/work/publications/papers/chi04.pdf). **E**; full text, methods inspected. Fifteen MIT computer-science graduate students participated in repeated short interviews over five days, supplemented by observation and longer interviews. Participants often approached targets through context rather than specifying a full query. It is exploratory, small, old and unusually technically skilled. **H:** preserve course/folder context and predictable browsing alongside search. Do not interpret the paper as a universal folder preference or a reason to remove search.

[Dumais et al., Stuff I've Seen, SIGIR 2003](https://www.microsoft.com/en-us/research/wp-content/uploads/2003/01/siscore-sigir2003-final.pdf). **E**; full text, retrieval and interface-evaluation sections inspected. More than 230 internal users tried a personal retrieval system; usage, questionnaires and deployed interface variants informed findings about contextual cues. Only 45 answered both before/after questionnaires. Time was a useful cue, but adoption and interface defaults confound simple causal claims. **H:** show course and meaningful change time; support re-finding old material rather than forcing recency everywhere. Their cross-application index is not an appropriate first scope for IliasSync.

[Bergman & Dvir, File hyper-searching explained, published online 2024, Human–Computer Interaction](https://doi.org/10.1080/07370024.2024.2379838). **E**; publisher abstract and indexed methods/limitations passages accessed; direct full-text request denied. Selected groups of 50 frequent searchers and 50 controls retrieved personal files. Group allocation used self-estimation and observed retrieval; the task supplied filenames and sampled MS Office documents. Group differences cannot show that searching causes poor organization, nor generalize directly to course PDFs. **H:** support both strategies and test wrong-file selections, not only retrieval speed. No personality-based personalization is justified.

## R5 — Interruptions can increase subjective cost even when speed improves

[Mark, Gudith & Klocke, The Cost of Interrupted Work: More Speed and Stress, CHI 2008](https://www.ics.uci.edu/~gmark/chi08-mark.pdf). **E**; full text, methods and results inspected. A counterbalanced laboratory experiment with 48 people, mostly German university students, compared interruption conditions during an email task. Participants compensated with faster work while reporting higher subjective cost. This does not establish a fixed recovery time or the effect of course notifications. **H:** distinguish useful awareness from interruption volume; measure errors and perceived burden with time.

[Fitz et al., Batching smartphone notifications can improve well-being, 2019, Computers in Human Behavior](https://doi.org/10.1016/j.chb.2019.07.016). **E**; publisher abstract/methods excerpts and [paper copy](https://static1.squarespace.com/static/57a40c19414fb54f51f8095f/t/614a55faa7b89e25f4e48ad1/1632261627146/2019%2Bfitz%2Bbatching.pdf) inspected. A two-week randomized field experiment with 237 participants compared usual alerts, two batching schedules and no alerts. Three daily batches improved some self-reports; hourly batching offered little change. The recruited Indian Android/MTurk sample, exploratory multiple outcomes and short duration limit transfer. **H:** investigate a user-controlled digest; the paper does not prescribe three daily academic notifications or justify any default alert frequency.

## R6 — Offline access addresses a plausible educational constraint

[Jisc, 2024/25 UK higher education student digital experience survey](https://digitalinsights.jisc.ac.uk/reports-and-briefings/our-reports/2024-25-uk-higher-education-students-digital-experience-insights-survey-findings/). **E**, primary organizational survey; report summary and sampling description accessed. There were 15,398 respondents at 30 UK providers, with unequal institutional contributions (one supplied 5,550). Sixty percent reported connectivity problems. This is self-report from participating providers, not a representative estimate for German ILIAS students, and does not measure demand for IliasSync. **H:** test offline readiness on students' actual destination types, including cloud-managed folders.

[Virtual Learning Environments: the students' perspective, Northumbria research record, 2007](https://researchportal.northumbria.ac.uk/en/publications/virtual-learning-environments-the-students-perspective/). **E**; institutional research abstract retrieved through search; direct page retrieval failed. A questionnaire (407), eight-week diary (14) and focus group (14) triangulated student accounts, identifying themes including structural consistency, learning materials and communication. Volunteer recruitment and an older VLE context limit generalization; the abstract provides no feature effect sizes. **H:** combine interviews with a short diary rather than relying on requested features alone.

[Jisc, Virtual learning environment review](https://www.jisc.ac.uk/guides/virtual-learning-environment-review). **C**, practitioner synthesis; relevant course-page sections accessed. Jisc reports inconsistent course organization as a recurring frustration in its review work. Sampling and causal estimates are not provided. **H:** preserve contextual labels, provide source access for exceptions and allow explicit aliases; do not silently infer lecture/week/topic structures.

## R7 — Measure a goal, then a signal, then a metric

[Rodden, Hutchinson & Fu, Measuring the User Experience on a Large Scale, CHI 2010](https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications/). **S**; original publication abstract accessed. HEART and goals–signals–metrics organize measurement using product-team examples; this is not a universal causal validation or a requirement for telemetry. **H:** prioritize task success, accurate status interpretation and recovery. Engagement and retention can mean a useful background routine; app-open duration is not the goal. [VALIDATION.md](VALIDATION.md) translates this framework into local research measures.

## R8 — Uncertain assistance needs correction and control

[Amershi et al., Guidelines for Human-AI Interaction, CHI 2019](https://www.microsoft.com/en-us/research/wp-content/uploads/2019/01/Guidelines-for-Human-AI-Interaction-camera-ready.pdf). **E/S**; original paper abstract, rationale and guideline table inspected. Iterative evaluation included 49 design practitioners and 20 AI products. This validates usefulness of guidelines, not the accuracy of future course summaries. **H:** any optional inference must expose limitations and support correction; do not introduce AI until an unresolved task justifies its privacy and maintenance costs. Deterministic change evidence should remain available independently.

## R9 — Mature desktop products make boundaries visible

These are **C**, documented behavior, not controlled studies or endorsements. Extract the contract, not the visual style.

| Primary source inspected | Useful principle | Transfer boundary |
| --- | --- | --- |
| [Syncthing file versioning](https://docs.syncthing.net/users/versioning.html) | Explain which changes are versioned and how retention works | Remote-change versioning is not a full backup of local edits; do not copy automatic cleanup defaults |
| [Dropbox Windows sync icons](https://help.dropbox.com/sync/sync-icons-windows) | Distinguish online-only, locally available and explicitly retained files | IliasSync does not own Dropbox state; file existence cannot substitute for provider residency evidence |
| [Qt QWidget accessibility](https://doc.qt.io/qt-6/accessible-qwidget.html) | Expose roles, states, actions and change events to assistive technology | Current docs describe newer Qt as well; verify availability against pinned Qt 6.10 and test actual screen readers |
| [PFERD configuration](https://github.com/Garmelon/PFERD/blob/master/CONFIG.md) | Make refresh/conflict policy explicit | Upstream master can differ from pinned 3.9.4; the local pinned source was inspected separately in [REVIEW.md](REVIEW.md) |

## What the evidence changes

The combined recommendation is to invest first in verifiable state, then in remembering changes on the student's behalf, while retaining context and ordinary files. The evidence does **not** prove that students want an unread inbox, local full-text search, a semester model or notifications. Those remain experiments. It also does not justify learning-outcome claims, diagnoses about attention or personality, or an exact notification schedule.

The least obvious implication is that **more visible automation can create more work**: sorting an inbox, investigating false “new” events, choosing classifications or responding to repeated status alerts. Evaluate the total workflow displaced, not the apparent sophistication of the feature.

The main broader evidence gap is observation beyond the product owner. No external interviews, diary study, representative compatibility study or user A/B test was performed in this session. On 28 October Nils explicitly chose to continue with his own use, independent agent reviews and deterministic scenarios because classmates are unavailable. That is the active [validation method](VALIDATION.md); external recruitment is optional. Reliability, clearer flows and accurate information can continue to improve without inventing population-level evidence or expanding the bibliography indefinitely.
