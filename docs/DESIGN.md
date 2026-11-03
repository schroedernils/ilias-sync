# Interface and content

The current visual rules live in [DESIGN-SYSTEM.md](DESIGN-SYSTEM.md). This file keeps the product decisions those rules have to preserve.

## Direct weekly schedule — November 2026

Settings → Schedule offers intervals or a weekly plan. Seven rows run Monday through Sunday, each with
directly editable 24-hour time fields, a remove action and an add button. An empty day explicitly says **No sync**.
**Copy times**, beside the battery option, progressively exposes applying one day's times to a single other weekday,
Monday–Friday or all seven days. Extra times wrap
inside their day; the settings body scrolls while the next planned run and Save/Cancel remain outside the scroll area.
Editing never resets a user-resized window. Every time/add/remove control has its weekday in its accessible name.

Legacy daily times populate all days in the draft; opening or cancelling settings changes neither stored policy nor
the OS job. Save atomically adopts the weekly plan and updates the native schedule, with the previous job and
configuration restored on installation failure. Empty enabled plans are rejected. Weekday numbering is normalized
Monday=0 internally, then translated to each native scheduler. Calendar preview skips nonexistent DST wall times.
The worker remains one-shot; no polling process is introduced.

Native calendar references: [Apple launchd](https://github.com/apple-oss-distributions/launchd/blob/main/man/launchd.plist.5),
[Windows weekly triggers](https://learn.microsoft.com/en-us/windows/win32/taskschd/weekly-trigger-example--xml-),
[systemd calendar expressions](https://www.freedesktop.org/software/systemd/man/255/systemd.time.html).

## Unified sync workspace — 1 November 2026

The default **Overview** shows up to three recently added/updated materials, their course context, an honest
problem count and **View all**. Older entries without tracked change times can fill empty slots; they display
no invented date. **Materials** retains scoped search, filters, newest-first defaults, keyboard actions and the
complete local library. **Notifications** and **Details** use the same content area rather than stacking panels.

One fixed bottom sync section contains **Sync now**, blue pause/resume and red stop buttons, current status,
last synchronization/attempt with absolute and relative time, and the next eligible automatic check. During an
active run, Sync now remains visible and disabled; dedicated pause and stop remain operable. Sign-in/storage
correction routes through the existing guided recovery. Stopping does not disable the schedule.

Notices are local, per-university, stable across repeated attempts and independent of sync evidence. Dismissal
hides a notice from the notification list, while Details offers **Show again**. It never marks a failed attempt
successful, deletes history, changes course selection or suppresses recovery. A completed recovery resolves the
notice; recurrence reopens it. Cancelled/in-progress attempts cannot resolve notices. System alerts are opt-in,
use generic lock-screen text, and are submitted by the headless worker only for new problems after macOS grants
permission. They use Apple's [UserNotifications authorization flow](https://developer.apple.com/documentation/usernotifications/asking-permission-to-use-notifications).

The following sections describe earlier iterations; the unified workspace above supersedes their panel placement.

## Material-first library and recovery — 29 October 2026

The current workspace starts with materials. The sidebar offers All materials and two levels of navigation:
university → course. Selecting a course filters the local library only; it never changes synchronization targets.
The university's (…) menu holds **Choose sync courses**, folder mapping, open folder and profile editing.
File opening remains directly available through double-click, Return, Cmd+O and the context menu. Cmd+F focuses
the scoped search. A View command and toolbar button hide/reveal the sidebar.

Rows use compact filename/context lines, extension-specific document marks and numeric size/date sorting.
Global results lead with university and course; course results lead with the local subfolder. Wide layouts expose
course/date columns, while compact layouts retain full metadata in accessible text and tooltips. Identical course
IDs and object IDs on different installations remain distinct, including custom destination roots. File classification
does not read or hydrate documents. No content or credentials are moved by browsing.

The former large status card and duplicated report buttons are replaced by one bottom status area. Healthy/idle
states remain compact; errors retain their explanation and a specific recovery action. Details expand inline, with
a scrollable report/guide at compact sizes. Attempt history, affected files, exclusions and technical evidence keep
their existing meanings. Successful synchronization with changes and a successful unchanged check use different
wording. Aggregates never promote one university's success to the entire library. A running university stays named
in the status even when the person browses another university; browsing remains enabled during work.

Recovery has an explicit completion loop: explain impact → specific correction → save and check → new verified
outcome or continued guidance. Expired sign-in opens a focused dialog with the affected university and the relevant
password/session controls. Cancel preserves the saved profile. Save and check starts a manual university check;
only a newly completed result for the correct configuration can confirm recovery. Warnings remain warnings even
after successful sign-in. File restoration additionally checks that the selected recorded file actually exists.
Network/storage causes are shown only when established by exception type/errno. Unknown causes stay unknown.
Server cooldowns and unavailable remote content explain why repeated immediate retries cannot repair access.

The hierarchy and scoped, continuously filtering search follow Apple's guidance for
[sidebars](https://developer.apple.com/design/human-interface-guidelines/sidebars) and
[search fields](https://developer.apple.com/design/human-interface-guidelines/search-fields).
This remains a Qt desktop application with native macOS interactions, rather than an AppKit/SwiftUI rewrite.
The sections below document earlier iterations and their retained behavioral constraints.

The default language is German; Settings offers an immediate switch to English. Server-provided course names and filenames keep their original wording. The interface uses the system typeface at 14px. Dark chrome is #141414 and the working pane is #181818, with #f0f0f0 text; light chrome is #f3f3f3 and the pane is #fcfcfc. The action blue is #599ce7. Hover fills fade in over 90ms, and a press darkens the control. The sync action morphs into pause and stop over about half a second. The window itself is slightly translucent. Keyboard focus stays visible.

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

The supplied IliasSync icon kit is the sole product identity. Native package icons and runtime window identity agree; UI marks use the supplied dark variant. Source editing lives in the sidebar on hover, right-click and F2. Folder actions sit beside the destination; settings is a gear. Actions retain translated accessible labels; hover help is limited to icons, meaningful consequences and clipped names rather than repeating visible text. Lucide 0.468.0 supplies a consistent action-icon family under its bundled license. Native Clear/Tinted macOS appearances require a separate Icon Composer document; classic ICNS is the current fallback.

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
