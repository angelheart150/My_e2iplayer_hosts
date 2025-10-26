#!/bin/sh
##############################################################
# E2IPlayer Hosts Auto Updater by Mohamed Elsafty
# Version: 1.2 (Final)
# Description: Update host*.py, extract .tar.gz archives,
# merge text files, and restart Enigma2
##############################################################
echo ''
echo '************************************************************'
echo '**         E2IPlayer Hosts Update Script                  **'
echo '************************************************************'
echo '**         Uploaded by: Mohamed Elsafty                   **'
echo '************************************************************'
sleep 2
DEST_DIR="/usr/lib/enigma2/python/Plugins/Extensions/IPTVPlayer"
TMP_DIR="/var/volatile/tmp/My_e2iplayer_hosts"
REPO_URL="https://github.com/angelheart150/My_e2iplayer_hosts"
DATE=$(date +%Y%m%d)
LOG_FILE="/tmp/e2iplayer_update.log"
COUNT=0
UPDATED_FILES=""
echo "> Removing any previous temporary folder..."
rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"
echo "> Downloading latest version from GitHub..."
wget -q --no-check-certificate "$REPO_URL/archive/refs/heads/main.zip" -O "$TMP_DIR/main.zip"
if [ ! -f "$TMP_DIR/main.zip" ]; then
    echo "!! Failed to download the zip file. Check internet connection or URL."
    exit 1
fi
echo "> Extracting archive..."
unzip -q "$TMP_DIR/main.zip" -d "$TMP_DIR"
SRC_DIR="$TMP_DIR/My_e2iplayer_hosts-main"
# ===========================================================
# 🧩 Extract any .tar.gz archives (like hostlodynet.tar.gz)
# ===========================================================
for tarfile in "$SRC_DIR"/*.tar.gz; do
    [ -f "$tarfile" ] || continue
    echo "> Extracting $(basename "$tarfile") ..."
    tar -xzf "$tarfile" -C "$SRC_DIR"
done
# ===========================================================
# Utility Functions
# ===========================================================
normalize_file() {
    f="$1"
    [ -f "$f" ] || return
    sed -i 's/\r$//' "$f"
    sed -i 's/[[:space:]]\+$//' "$f"
    sed -i '/./,$!d' "$f"
    sed -i -e '$a\' "$f"
}
sort_list_file() {
    f="$1"
    normalize_file "$f"
    grep -v '^[[:space:]]*$' "$f" | sort -u > "${f}.tmp"
    mv "${f}.tmp" "$f"
    sed -i '/^[[:space:]]*$/d' "$f"
    sed -i '/./,$!d' "$f"
}
sort_aliases_file() {
    f="$1"
    normalize_file "$f"
    awk '
    BEGIN { inblock=0 }
    /^{/ { print; inblock=1; next }
    /^}/ { close("sort"); inblock=0; print; next }
    inblock { print | "sort" }
    !inblock && !/^[{}]/ { print }
    ' "$f" > "${f}.tmp"
    mv "${f}.tmp" "$f"
    sed -i '/./,$!d' "$f"
}
sort_arabic_group() {
    f="$1"
    normalize_file "$f"
    ln_start=$(grep -n '"arabic"' "$f" | head -n1 | cut -d: -f1)
    [ -z "$ln_start" ] && return
    ln_end=$(awk "NR>$ln_start && /^[[:space:]]*]/ {print NR; exit}" "$f")
    [ -z "$ln_end" ] && return
    head -n "$ln_start" "$f" > "${f}.tmp"
    entries=$(sed -n "$((ln_start+1)),$((ln_end-1))p" "$f" | sed -n 's/^[[:space:]]*"\(.*\)".*/\1/p' | sort -u)
    total=$(echo "$entries" | wc -l | tr -d ' ')
    idx=0
    echo "$entries" | while IFS= read -r h; do
        idx=$((idx+1))
        [ -z "$h" ] && continue
        if [ "$idx" -lt "$total" ]; then
            echo "  \"$h\"," >> "${f}.tmp"
        else
            echo "  \"$h\"" >> "${f}.tmp"
        fi
    done
    tail -n +"$ln_end" "$f" >> "${f}.tmp"
    mv "${f}.tmp" "$f"
    normalize_file "$f"
    echo "✅ Arabic group sorted and cleaned." | tee -a "$LOG_FILE"
}
# ===========================================================
# Backup and update host*.py
# ===========================================================
for file in "$SRC_DIR"/host*.py; do
    [ -f "$file" ] || continue
    filename=$(basename "$file")
    destfile="$DEST_DIR/$filename"
    echo "Checking for old backups of $filename..."
    find "$DEST_DIR" -maxdepth 1 -type f -name "$filename.*.bak" ! -name "$filename.$DATE.bak" -exec rm -f {} \;
    if [ -f "$destfile" ]; then
        echo "Backing up $filename -> $filename.$DATE.bak"
        mv "$destfile" "$destfile.$DATE.bak"
    fi
    echo "Installing $filename"
    cp -f "$file" "$DEST_DIR/"
    UPDATED_FILES="$UPDATED_FILES\n$filename"
    COUNT=$((COUNT+1))
done
# ===========================================================
# Merge text files (append new unique lines only)
# ===========================================================
merge_text_file() {
    src="$1"
    dst="$2"
    [ -f "$src" ] || return
    [ -f "$dst" ] || touch "$dst"
    normalize_file "$src"
    normalize_file "$dst"
    grep -Fxvf "$dst" "$src" >> "$dst"
    echo "Merged new entries into $(basename "$dst")"
}
merge_text_file "$SRC_DIR/aliases.txt" "$DEST_DIR/hosts/aliases.txt"
merge_text_file "$SRC_DIR/hostgroups.txt" "$DEST_DIR/hosts/hostgroups.txt"
merge_text_file "$SRC_DIR/list.txt" "$DEST_DIR/hosts/list.txt"
sort_aliases_file "$DEST_DIR/hosts/aliases.txt"
sort_arabic_group "$DEST_DIR/hosts/hostgroups.txt"
sort_list_file "$DEST_DIR/hosts/list.txt"
# ===========================================================
# Cleanup
# ===========================================================
rm -rf "$TMP_DIR"
sync
echo '************************************************************'
echo "** INSTALLATION DONE - $COUNT host file(s) updated **"
echo '************************************************************'
echo "$(date): Updated $COUNT file(s)" >> "$LOG_FILE"
echo -e "Updated files:$UPDATED_FILES"
sleep 2
echo "Restarting Enigma2..."
killall -9 enigma2
exit 0