# IliasSync design system

These are the rules the interface already follows. Change the product by extending them, not by adding a one-off.

## Surfaces

On macOS the window content uses `FROST` (0.87). Only the strip behind the native window controls uses a lighter tint (0.54), following Qt's title bar inset. Nested layout carriers, scrolling pages and material tables remain transparent so they cannot multiply the content opacity. Sidebar and card fills are light overlays (0.26 dark, 0.46 light), with their colors compensated to retain the same contrast over the window. Fields use the same backdrop with a slightly denser overlay. Other desktop backends retain solid surfaces. Dark rails are lifted 12 steps and cards 18. Menus and choice lists use a separate 0.98 opacity so content behind them cannot compete with their labels. High contrast makes all surfaces opaque.

The desktop behind the window is a smooth blur (radius 52) with a restrained native tint (0.26 dark, 0.34 light) that keeps bright backgrounds from punching through. The blur view sits behind Qt’s view. Do not reparent that view or replace the window content view. Do not fade the whole window with `setWindowOpacity`; that fades the type as well. High contrast turns the frost fully opaque.

Accent buttons, the commit button and input borders stay solid so they remain readable on the veil.

Settings tabs and scroll viewports stay transparent over the continuous window background. General and schedule content use the same rounded card surface as the overview, with 16px of inner padding; notification cards sit directly on the window background. Fields sit one brightness step above the cards. Do not fill unused tab space with a separate dark rectangle.

Tab widgets, tab bars and dialog button boxes also have transparent backgrounds; styling only the tab items and pane leaves a separate opaque container. Refresh the native tint after applying the new stylesheet on theme changes.

Apply Aqua/Dark Aqua to each Cocoa window with that tint, including the title bar. Do not change the macOS system appearance or the global application appearance. Preview, Cancel and repeated theme changes must update every open window.

## Color

Dark window `#181818`, text `#f0f0f0`, muted `#b8b8b8`. The light palette uses a soft gray-white window (`#e8eae8`), lifted paper cards (`#f2f3f0`) and graphite text (`#303936`), with readable secondary ink (`#57635e`). Selection is a pale gray-green, never a charcoal chip with dark ink. Light actions use muted blue (`#a4cbe1`) and deep blue ink (`#233e4d`); dark actions retain `#599ce7`. The save control remains the bright commit color (`#d7ebff` in dark mode). Errors, success and warnings keep their own hues. Input borders stay at least 3:1 against both the window and the surface.

Item delegates choose their theme from text ink rather than transparent Base/Window brushes, which Qt can report as black. Theme changes must update the row fill, metadata and icons together.

## Shape

Controls use a 10px radius. Rows, menus, popups and cards use 12px. Icon buttons are circles. A hover or selection is one rounded chip. It never sits inside a second square, and the style’s own highlight rectangle stays transparent. Popup windows are masked to the same radius so the system window does not draw a square frame around them.

## Hover and press

Hover help is reserved for icon-only controls, important action consequences and full names/context that are visibly clipped. Do not repeat readable status headings, search placeholders, field contents or navigation labels. Keep exact sync times and next-run facts available in concise help and accessibility text. Useful hints use a short bold heading, at most one brief explanation, a narrow readable layout and a quiet rounded surface. Explanations and recovery remain available through the normal interface; hover is never required to operate the app.

One wash for rows, menus and ghost buttons: white at alpha 78 on dark, black at alpha 28 on light. Button washes ease in over 180ms and out over 220ms; reversing direction starts at the current brightness. Colored actions use a subtler wash and keep their hue. Button labels and icons are painted above the wash, so they stay readable. In the sidebar that area is the name itself; the gutter to its left, including the disclosure, does not light up. A click does not replay it. Opening a menu clears the wash and restores it afterward only if the pointer is still on the control. Buttons do not get a blue focus ring. Text fields and combos still show an accent focus border.

Help topics keep hover separate from selection, with the selected fill taking precedence. Pointer changes, leaving, scrolling and focus changes recompose the translucent dialog background so prior text and chips do not accumulate. Keyboard selection remains visible and continues to update the help article; the article viewport stays transparent.

## Motion that must not shove layout

The sync area is one inset card, aligned with the materials and overview on both sides. In the resting state, the outcome, last run (clock time and age) and next check form one text group beside the primary action. The status symbol carries meaning as well as color. During an active run, the explanation and time labels sit together between the heading and progress track, with balanced spacing. When an error has a specific recovery action, that action takes the primary slot and the explanation uses the full text column below it. At tight widths, the action slot can move below the heading group instead of squeezing the text or clipping a control.

The sync action morphs into pause and stop over 640ms on a fixed rectangle. Pause settles into a neutral gray in dark mode and a muted amber in light mode; stop retains its red fill. Pause ink, hover/pressed states and the animated fill share one palette. The button transformation does not move neighboring content. Menus open with a short fade at their Qt-constrained position. They close immediately.

Buttons reached by Tab or a keyboard shortcut show an inset focus outline in the control's own ink. Mouse clicks keep the normal pressed and hover treatment. Inactive tabs and time labels use the same legible secondary ink on translucent and solid surfaces.

## Type and language

The system font, German by default, English from Settings. Names from the server stay as they are. Row titles are medium, secondary lines are muted and smaller. Elide the end of a sidebar label, not the middle.

## Content

The sidebar resizes live from 200 to 480px, while the content retains at least 500px. Search adapts to the remaining width. Resizing repaints the translucent workspace, and the chosen sidebar width is restored with the window state.

Overview first. The recent-files card hugs its rows. The sync strip runs the full width to the sidebar edge and keeps a reserved gap under the status and buttons. The progress stroke is 4px and sits in that gap, so the line has room above and below without pushing the text. Notifications live in Settings, not on the start screen. Status copy is a short heading plus one fact. A missing local file says so and offers a repair, instead of failing silently.
