#!/bin/sh
##############################################################
# E2IPlayer Hosts Auto Updater by Mohamed Elsafty
# Version: 1.2 (Final)
# Description: Update host*.py, extract .tar.gz archives,
# merge text files, and restart Enigma2
##############################################################
#setup command=wget -q "--no-check-certificate" https://github.com/angelheart150/My_e2iplayer_hosts/raw/main/install-e2iplayer-update-hosts.sh -O - | /bin/sh
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
# 🧩 Extract the main tar.gz to ROOT filesystem
# ===========================================================
echo "> Extracting main host files to system..."
MAIN_TAR="$SRC_DIR/My_e2iplayer_hosts.tar.gz"
if [ -f "$MAIN_TAR" ]; then
    echo "✓ Extracting $(basename "$MAIN_TAR") to /"
    tar xzvpf "$MAIN_TAR" -C /
else
    echo "!! Main host archive not found: $MAIN_TAR"
    exit 1
fi
# ===========================================================
# 🧩 Extract any additional .tar.gz archives
# ===========================================================
for tarfile in "$SRC_DIR"/*.tar.gz; do
    [ "$tarfile" = "$MAIN_TAR" ] && continue
    [ -f "$tarfile" ] || continue
    echo "> Extracting additional archive: $(basename "$tarfile") ..."
    tar -xzf "$tarfile" -C "$SRC_DIR"
done
# ===========================================================
# Utility Functions
# ===========================================================
normalize_file() {
    f="$1"
    [ -f "$f" ] || return
    sed -i 's/\r$//' "$f" 2>/dev/null
    sed -i 's/[[:space:]]\+$//' "$f" 2>/dev/null
    sed -i '/./,$!d' "$f" 2>/dev/null
    sed -i -e '$a\' "$f" 2>/dev/null
}
sort_list_file() {
    f="$1"
    normalize_file "$f"
    grep -v '^[[:space:]]*$' "$f" | sort -u > "${f}.tmp" 2>/dev/null
    [ -f "${f}.tmp" ] && mv "${f}.tmp" "$f" 2>/dev/null
    sed -i '/^[[:space:]]*$/d' "$f" 2>/dev/null
    sed -i '/./,$!d' "$f" 2>/dev/null
}
sort_aliases_file() {
    f="$1"
    normalize_file "$f"
    # استخدام grep و sed بدلاً من awk للمشاكل regex
    if grep -q '^{' "$f" 2>/dev/null; then
        temp_file="${f}.temp"
        > "$temp_file"
        in_block=0
        block_content=""
        while IFS= read -r line; do
            if echo "$line" | grep -q '^{'; then
                in_block=1
                block_content=""
                echo "$line" >> "$temp_file"
            elif echo "$line" | grep -q '^}'; then
                in_block=0
                printf "%b" "$block_content" | sort >> "$temp_file"
                echo "$line" >> "$temp_file"
            elif [ $in_block -eq 1 ]; then
                block_content="${block_content}${line}\n"
            else
                echo "$line" >> "$temp_file"
            fi
        done < "$f"
        [ -f "$temp_file" ] && mv "$temp_file" "$f" 2>/dev/null
    fi
    normalize_file "$f"
}
sort_arabic_group() {
    f="$1"
    normalize_file "$f"
    ln_start=$(grep -n '"arabic"' "$f" 2>/dev/null | head -n1 | cut -d: -f1)
    [ -z "$ln_start" ] && return
    ln_end=$(awk "NR>$ln_start && /^[[:space:]]*]/ {print NR; exit}" "$f" 2>/dev/null)
    [ -z "$ln_end" ] && return
    head -n "$ln_start" "$f" > "${f}.tmp" 2>/dev/null
    entries=$(sed -n "$((ln_start+1)),$((ln_end-1))p" "$f" 2>/dev/null | sed -n 's/^[[:space:]]*"\(.*\)".*/\1/p' | sort -u)
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
    tail -n +"$ln_end" "$f" >> "${f}.tmp" 2>/dev/null
    [ -f "${f}.tmp" ] && mv "${f}.tmp" "$f" 2>/dev/null
    normalize_file "$f"
    echo "✅ Arabic group sorted and cleaned." | tee -a "$LOG_FILE"
}
# ===========================================================
# Backup and update host*.py (from extracted archives)
# ===========================================================
echo "> Creating backups and updating host files..."
for file in $(find "$SRC_DIR" -name "host*.py"); do
    [ -f "$file" ] || continue
    filename=$(basename "$file")
    destfile="$DEST_DIR/$filename"
    echo "Checking for old backups of $filename..."
    find "$DEST_DIR" -maxdepth 1 -type f -name "$filename.*.bak" ! -name "$filename.$DATE.bak" -exec rm -f {} \; 2>/dev/null
    if [ -f "$destfile" ]; then
        echo "Backing up $filename -> $filename.$DATE.bak"
        cp -f "$destfile" "$destfile.$DATE.bak" 2>/dev/null
    fi
    echo "Installing $filename"
    cp -f "$file" "$DEST_DIR/" 2>/dev/null
    if [ $? -eq 0 ]; then
        UPDATED_FILES="$UPDATED_FILES $filename"
        COUNT=$((COUNT+1))
        echo "✓ Successfully installed $filename"
    else
        echo "✗ Failed to install $filename"
    fi
done
# ===========================================================
# Merge text files (append new unique lines only)
# ===========================================================
merge_text_file() {
    src="$1"
    dst="$2"
    [ -f "$src" ] || { echo "Source file $src not found"; return; }
    [ -f "$dst" ] || { echo "Creating $dst"; touch "$dst"; }
    normalize_file "$src"
    normalize_file "$dst"
    new_entries=$(grep -Fxvf "$dst" "$src" 2>/dev/null | wc -l)
    grep -Fxvf "$dst" "$src" >> "$dst" 2>/dev/null
    echo "Merged $new_entries new entries into $(basename "$dst")"
}
echo "> Merging and sorting text files..."
[ -f "$SRC_DIR/aliases.txt" ] && merge_text_file "$SRC_DIR/aliases.txt" "$DEST_DIR/hosts/aliases.txt"
[ -f "$SRC_DIR/hostgroups.txt" ] && merge_text_file "$SRC_DIR/hostgroups.txt" "$DEST_DIR/hosts/hostgroups.txt"
[ -f "$SRC_DIR/list.txt" ] && merge_text_file "$SRC_DIR/list.txt" "$DEST_DIR/hosts/list.txt"
[ -f "$DEST_DIR/hosts/aliases.txt" ] && sort_aliases_file "$DEST_DIR/hosts/aliases.txt"
[ -f "$DEST_DIR/hosts/hostgroups.txt" ] && sort_arabic_group "$DEST_DIR/hosts/hostgroups.txt"
[ -f "$DEST_DIR/hosts/list.txt" ] && sort_list_file "$DEST_DIR/hosts/list.txt"
# ===========================================================
# Cleanup
# ===========================================================
rm -rf "$TMP_DIR"
sync
echo '************************************************************'
echo "** INSTALLATION DONE - $COUNT host file(s) updated **"
echo '************************************************************'
echo "$(date): Updated $COUNT file(s)" >> "$LOG_FILE"
if [ $COUNT -gt 0 ]; then
    echo "Updated files:$UPDATED_FILES"
else
    echo "No additional host files were updated from archives!"
fi
sleep 2
echo "Restarting Enigma2..."
killall -9 enigma2
exit 0