# IliasSync – Icon-Kit

Basierend auf der freigegebenen Vorschau: weißer ILIAS-Schriftzug, gelbes Sync-Symbol mit Farbverlauf, petrolblauer Hintergrund. Keine getrennten Initialen oder Monogramme.

## Schnell verwenden
- macOS/IliasSync.icns: sofort verwendbares klassisches macOS-App-Icon mit transparentem Außenrand und abgerundeter Kachel.
- macOS/Assets.xcassets: klassischer Xcode-AppIcon-Assetkatalog mit allen zehn Mac-Größen (16, 32, 128, 256 und 512 pt in 1x/2x).
- macOS/IliasSync-Dark.icns: vorbereitete dunkle Alternative. Sie wechselt nicht von sich aus mit dem Systemmodus.
- PNG/Default und PNG/Dark: vollflächige quadratische Master und Rasterexporte. Die Formmaske ist hier absichtlich nicht eingebrannt.
- PNG/Transparent: nur ILIAS-Schriftzug und Sync-Symbol, ohne Hintergrund; farbig sowie weiß und schwarz.
- SVG: echte skalierbare Pfade, auch der Schriftzug ist in Pfade umgewandelt. Keine Schriften oder eingebetteten Bitmaps nötig.
- macOS/SyncTemplate-*.png: kompaktes monochromes Sync-Symbol für die Menüleiste. Im Code als Template-Image konfigurieren, z. B. NSImage.isTemplate = true. Das ist ein Menüleistensymbol, kein adaptives App-Icon.

## Moderne macOS-Darstellungen: Icon Composer
Die getrennten Quellen liegen in Icon-Composer-Layers. Alle haben dieselbe 1024×1024-Zeichenfläche und sind ohne Verschieben übereinander importierbar:
1. Hintergrund: 01-Background.svg. Alternativ den passenden blauen Hintergrund in Icon Composer einstellen.
2. Symbol: 02-Sync.svg.
3. Schrift: 03-Wordmark.svg.
Foreground-Mono.svg ist eine optionale gemeinsame monochrome Vordergrundquelle; nicht zusätzlich über die farbigen Ebenen legen.

In Apples Icon Composer importieren, Default/Dark/Mono sowie die daraus erzeugten Clear-/Tinted-Vorschauen prüfen, dann als .icon sichern und im Xcode-Projekt verwenden. Die aktuelle transparente Vordergrunddatei allein ist noch kein adaptives .icon-Dokument. Eine klassische .icns-Datei enthält keine separat konfigurierten modernen Darstellungen. Die native .icon-Datei muss auf dem Mac in Icon Composer erstellt werden; sie ist in diesem Paket nicht enthalten.

## Gestaltung und Treue
Reference/Approved-Preview.png ist die unveränderte, freigegebene Rastervorschau. Für saubere Exporte wurden die Konturen direkt aus dieser Vorlage vektorisiert; weder Text noch Symbol wurden neu entworfen. Sehr feine Rastertextur wurde durch glatte editierbare Farbverläufe ersetzt. Die klassische ICNS verwendet zusätzlich einen transparenten Außenrand; die Composer-Master bleiben vollflächig quadratisch.

## Apple-Dokumentation
https://developer.apple.com/icon-composer/
https://developer.apple.com/documentation/xcode/creating-your-app-icon-using-icon-composer

## Dateien
Die normalen SVGs und PNGs sind Grafiken. Die dunkle Variante ist eine bewusst vorbereitete Farbvariante. Clear/Tinted werden nicht als vermeintlich native statische PNGs simuliert; dafür sind die separaten Vordergrundebenen vorhanden.
