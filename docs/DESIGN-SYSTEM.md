# IliasSync design system

These are the rules the interface already follows. Change the product by extending them, not by adding a one-off.

## Surfaces

Window surfaces use `FROST` (0.76); dark rails are lifted 12 steps and cards 18. Menus and choice lists use a separate 0.97 opacity so content behind them cannot compete with their labels. High contrast makes them opaque.

The desktop behind the window is a smooth blur (radius 52) with a tint that keeps bright backgrounds from punching through. The blur view sits behind Qt’s view. Do not reparent that view or replace the window content view. Do not fade the whole window with `setWindowOpacity`; that fades the type as well. High contrast turns the frost fully opaque.

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

One wash for rows, menus and ghost buttons: white at alpha 78 on dark, black at alpha 28 on light. It fades in over 90ms and out over 110ms, and only while the pointer is over the control. In the sidebar that area is the name itself; the gutter to its left, including the disclosure, does not light up. A click does not replay it. Opening a menu clears the wash and restores it afterward only if the pointer is still on the control. Buttons do not get a blue focus ring. Text fields and combos still show an accent focus border.

Help topics keep hover separate from selection, with the selected fill taking precedence. Pointer changes, leaving, scrolling and focus changes recompose the translucent dialog background so prior text and chips do not accumulate. Keyboard selection remains visible and continues to update the help article; the article viewport stays transparent.

## Motion that must not shove layout

The sync action morphs into pause and stop over 640ms on a fixed rectangle. Pause settles into a neutral gray in dark mode and a muted amber in light mode; stop retains its red fill. Pause ink, hover/pressed states and the animated fill share one palette. Labels, the status line and the neighboring controls do not move. Menus open with a short fade and a 6px rise. They close immediately.

## Type and language

The system font, German by default, English from Settings. Names from the server stay as they are. Row titles are medium, secondary lines are muted and smaller. Elide the end of a sidebar label, not the middle.

## Content

The sidebar resizes live from 200 to 480px, while the content retains at least 500px. Search adapts to the remaining width. Resizing repaints the translucent workspace, and the chosen sidebar width is restored with the window state.

Overview first. The recent-files card hugs its rows. The sync strip runs the full width to the sidebar edge and keeps a reserved gap under the status and buttons. The progress stroke is 4px and sits in that gap, so the line has room above and below without pushing the text. Notifications live in Settings, not on the start screen. Status copy is a short heading plus one fact. A missing local file says so and offers a repair, instead of failing silently.
