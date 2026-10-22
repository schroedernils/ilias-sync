#!/bin/sh
# Optional, user-invoked Linux launcher. Keep the unpacked app at this location.
set -eu
app_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
desktop_dir=${XDG_DATA_HOME:-"$HOME/.local/share"}/applications
mkdir -p "$desktop_dir"
# Desktop Exec has its own quoting rules, independent of shell quoting.
executable=$(printf '%s' "$app_dir/IliasSync" | sed 's/\\/\\\\/g; s/"/\\"/g; s/`/\\`/g; s/\$/\\$/g; s/%/%%/g')
printf '%s\n' '[Desktop Entry]' 'Type=Application' 'Name=IliasSync' \
  'Comment=Keep ILIAS course files on this computer' \
  'Comment[de]=ILIAS-Kursdateien auf diesem Computer synchronisieren' \
  "Exec=\"$executable\"" "Icon=$app_dir/IliasSync.png" 'Terminal=false' \
  'Categories=Education;Network;' 'StartupWMClass=IliasSync' \
  > "$desktop_dir/org.iliassync.desktop.desktop"
printf '%s\n' "$desktop_dir/org.iliassync.desktop.desktop"
