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
