# Interface and content

The default language is German; Settings offers an immediate switch to English. Server-provided course names and filenames keep their original wording. The interface uses system typography, a quiet neutral palette, a single blue action accent, visible keyboard focus and standard desktop controls.

The main view answers: which ILIAS, where are my files, what happened, what can I do next? Marketing headings, repeated privacy claims, the permanent version footer and empty activity console were removed. Detailed activity is expandable. The login form only shows fields needed by the selected method. Errors explain the next action; unavailable and skipped content remains visible in the result. A lack of content is not represented as a successful full archive.

Design references inform decisions rather than copying brand assets:

- [Apple: Principles of great design](https://developer.apple.com/videos/play/wwdc2026/250/): hierarchy through order and spacing, concise language, standard controls.
- [OpenAI: Design guidelines](https://openai.com/brand/): measured typography, clear space and approachable geometry. No OpenAI typeface or branding is bundled.
- [Stripe: Design your app](https://docs.stripe.com/stripe-apps/design): consistent components, restrained styling, accessible contrast.
- [Meta: Content design](https://www.meta.com/design-at-meta/blog/why-were-moving-from-content-strategy-to-content-design/): direct, human language, words and interactions designed together.

These references are not endorsements. Qt Widgets provides a native desktop runtime; this is not a SwiftUI, WinUI or GTK application.


## Alpha 2 correction

The initial native macOS form mixed hard-coded light text with a system-dark scroll surface, and native form growth left narrow inputs. The correction explicitly defines every palette role, scroll background, input surface and disabled state in both schemes. `QStyleHints.colorSchemeChanged` updates the complete application palette; default follows the OS, with light/dark overrides in settings. The accepted workspace layout is retained.

A local REA investigation identified the installed artifacts for ChatGPT, Google Drive, Spotify and Discord. Selected shipped CSS was inspected separately for semantic surface and state tokens; CSS-only graphs are asset inventory, not JavaScript behavioral evidence. Discord analysis covered its packaged bootstrap, not the full remotely loaded client. ChatGPT live UI was unavailable to the computer-use provider. Google Drive's actual dark preferences window was observed after explicit permission. GitHub Desktop and LocalSend were additional local candidates; native LocalSend metadata alone did not establish its UI behavior. Extracts, raw evidence and account-bearing screenshots are excluded from Git.

Setup now separates university address, sign-in and files into three steps. Settings groups language/theme and background policy. The start button becomes Pause/Resume plus Stop during work. Stop ends this batch; a configured schedule remains enabled for its next run. No reference branding or source code is shipped.

The supplied IliasSync icon kit is the sole product identity. Native package icons and runtime window identity agree; UI marks use the supplied dark variant. Source editing lives in the sidebar on hover, right-click and F2. Folder actions sit beside the destination; settings is a gear. All retain translated accessible labels and tooltips. Lucide 0.468.0 supplies a consistent action-icon family under its bundled license. Native Clear/Tinted macOS appearances require a separate Icon Composer document; classic ICNS is the current fallback.

## Materials and synchronization redesign (October 2026)

The primary job is to know whether the local materials are current and to open the right file. The former view gave
roughly equal weight to product branding, an absolute cloud path, configuration actions and an undifferentiated manifest.
A status-first desktop shell and a separate overview page were considered. The implemented single-workspace library
keeps the answer and the files together; a separate dashboard would add navigation for the same task.

A compact university sidebar owns sources, background schedule and settings. The content area owns the current source,
a compact destination label (full path remains in its tooltip), synchronization health and materials. Folder actions stay
beside course selection. There is one primary sync action, becoming pause/resume during a run, with a distinct stop control.
No decorative animation or fabricated percentage is introduced; an indeterminate progress track appears only while active.

Filename-first rows keep the course/folder visible as secondary context, distinguish duplicate filenames and support native
selection, keyboard navigation, double-click/Enter opening and an inline search with Cmd/Ctrl+F. Recently changed files use
persisted publication times; existing material does not get false "new" labels. Course descriptions and generated links are
available in a separate view rather than overwhelming the everyday material list. Filtering and numeric size sorting remain.

The status uses words and a symbol as well as color. Unavailable downloads and local edits produce an explanatory note;
actual failures and expired authentication provide specific recovery. Excluded forums/tests/groups are explained in the
report, rather than appearing as failed file downloads. Readable results precede optional technical activity. Synthetic
status, course and file strings are treated as text, including HTML-like filenames. Existing credentials, manifests, folder
rules, archive protection and schedule behavior remain compatible.

The choices follow [Nielsen's heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/) on visible status,
recognition, error recovery and information priority, [Apple's button guidance](https://developer.apple.com/design/human-interface-guidelines/buttons)
on clear actions and restrained prominence, and [Qt's accessibility guidance](https://doc.qt.io/qt-6/accessible.html)
on semantic controls, keyboard access and non-color feedback. These are design rationales, not evidence of a user study
or a claim of universal platform certification.

`review_interface.py` renders synthetic first-run, loading, success, partial, error, login, search, recent, pause, stopping,
setup, mapping and schedule states in both palettes, including a compact window. Functional tests cover actual header
clicks, combined filters, file selection and Enter opening, status classification, recovery actions, source switching,
publication history, progress notifications and no idle polling. Rendered inspection and local runtime checks supplement
the test suite; they do not establish screen-reader compatibility on every supported OS.

The second workflow pass replaces multi-column routing rules with a hierarchy and selected-item properties, showing
the effective path and inheritance explicitly. Add-source setup remains guided; editing uses direct tabs. Settings share
one draft/Save/Cancel contract, while help is read-only and organized by topic. Time editing handles selection, duplicate
prevention and removal; the body scrolls when text is enlarged. Reports expose known causes, scope and attempt history
without substituting old counts for a new failure. Success wording names the completed historical check, rather than
asserting perpetual freshness. Legacy scope and count data stay unknown where they were never recorded.

Compact status panels reserve space for wrapped text; long source labels retain full accessible names and tooltips.
Input/checkbox boundaries use stronger contrast than decorative separators. Platform high-contrast preferences use
the native palette. These accommodations have synthetic checks; native assistive-technology certification remains open.
