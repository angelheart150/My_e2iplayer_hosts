#!/bin/sh
##############################################################
# E2IPlayer Hosts Auto Updater by Mohamed Elsafty
# Version: 3.3 (Fixed Temp Cleanup)
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
HOSTS_DIR="$DEST_DIR/hosts"
TAR_FILE="/tmp/My_e2iplayer_hosts.tar.gz"
REPO_URL="https://github.com/angelheart150/My_e2iplayer_hosts/raw/main/My_e2iplayer_hosts.tar.gz"
DATE=$(date +%Y%m%d)
LOG_FILE="/tmp/e2iplayer_update.log"
# Counters
NEW_HOSTS_COUNT=0
NEW_ALIASES=0
NEW_LIST_ENTRIES=0
NEW_HOSTGROUPS=0
# ===========================================================
# Utility Functions
# ===========================================================
backup_file() {
    local file="$1"
    if [ -f "$file" ]; then
        local backup="${file}.${DATE}.bak"
        cp -f "$file" "$backup"
        echo "📦 Backed up: $(basename "$file") → $(basename "$backup")" | tee -a "$LOG_FILE"
    fi
}
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
        /^\{/ { print; inblock=1; next }
        /^\}/ { close("sort"); inblock=0; print; next }
        inblock { print | "sort" }
        !inblock && !/^[{}]/ { print }
    ' "$f" > "${f}.tmp"
    mv "${f}.tmp" "$f"
    sed -i '/./,$!d' "$f"
}
sort_arabic_group() {
    f="$1"
    normalize_file "$f"
    ln_start=$(grep -n "\"arabic\"" "$f" | head -n1 | cut -d: -f1)
    [ -z "$ln_start" ] && return
    ln_end=$(awk "NR>$ln_start && /^\s*]/ {print NR; exit}" "$f")
    [ -z "$ln_end" ] && return
    head -n "$ln_start" "$f" > "${f}.tmp"
    entries=$(sed -n "$((ln_start+1)),$((ln_end-1))p" "$f" | \
        sed -n 's/^[[:space:]]*"\(.*\)".*/\1/p' | sort -u)
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
# Extract Host Information from Python File
# ===========================================================
extract_host_info() {
    local host_file="$1"
    local host_info=""
    local host_name=$(basename "$host_file" .py)
    local host_url=$(grep "def gettytul()" "$host_file" -A 1 | grep "return" | head -1 | sed "s/.*return[[:space:]]*['\"]\([^'\"]*\)['\"].*/\1/")
    echo "$host_name|$host_url"
}
# ===========================================================
# Extract and Compare Host Files
# ===========================================================
extract_and_compare_hosts() {
    echo "🔍 Extracting and comparing host files..." | tee -a "$LOG_FILE"
    TEMP_EXTRACT="/tmp/e2i_extract_$$"
    mkdir -p "$TEMP_EXTRACT"
    tar xzpf "$TAR_FILE" -C "$TEMP_EXTRACT" >/dev/null 2>&1
    NEW_HOSTS=""
    for host_file in "$TEMP_EXTRACT"/usr/lib/enigma2/python/Plugins/Extensions/IPTVPlayer/hosts/host*.py; do
        [ -f "$host_file" ] || continue
        filename=$(basename "$host_file")
        dest_file="$HOSTS_DIR/$filename"
        if [ ! -f "$dest_file" ]; then
            NEW_HOSTS="$NEW_HOSTS $host_file"
            NEW_HOSTS_COUNT=$((NEW_HOSTS_COUNT + 1))
            echo "🆕 New host found: $filename" | tee -a "$LOG_FILE"
        else
            if ! cmp -s "$host_file" "$dest_file"; then
                backup_file "$dest_file"
                echo "🔄 Updating modified: $filename" | tee -a "$LOG_FILE"
            else
                echo "ℹ️  No changes: $filename" | tee -a "$LOG_FILE"
            fi
        fi
    done
    echo "🧹 Cleaning temporary extraction folder..." | tee -a "$LOG_FILE"
    rm -rf "$TEMP_EXTRACT"
    echo "✅ Comparison completed - $NEW_HOSTS_COUNT new host(s)" | tee -a "$LOG_FILE"
}
# ===========================================================
# Update Text Files
# ===========================================================
update_aliases_file() {
    echo "📝 Updating aliases.txt..." | tee -a "$LOG_FILE"
    ALIASES_FILE="$HOSTS_DIR/aliases.txt"
    backup_file "$ALIASES_FILE"
    for host_file in $NEW_HOSTS; do
        [ ! -f "$host_file" ] && continue
        host_info=$(extract_host_info "$host_file")
        host_name=$(echo "$host_info" | cut -d'|' -f1)
        host_url=$(echo "$host_info" | cut -d'|' -f2)
        [ -z "$host_name" ] && continue
        formatted="'$host_name': '$host_url',"
        if ! grep -q "'$host_name':" "$ALIASES_FILE"; then
            sed -i "/^{/a $formatted" "$ALIASES_FILE"
            echo "➕ Added alias: $formatted" | tee -a "$LOG_FILE"
            NEW_ALIASES=$((NEW_ALIASES + 1))
        else
            echo "ℹ️  Alias for $host_name already exists" | tee -a "$LOG_FILE"
        fi
    done
    sort_aliases_file "$ALIASES_FILE"
    echo "✅ aliases.txt updated." | tee -a "$LOG_FILE"
}
update_list_file() {
    echo "📝 Updating list.txt..." | tee -a "$LOG_FILE"
    LIST_FILE="$HOSTS_DIR/list.txt"
    backup_file "$LIST_FILE"
    normalize_file "$LIST_FILE"
    for host_file in $NEW_HOSTS; do
        [ ! -f "$host_file" ] && continue
        host_name=$(basename "$host_file" .py)
        clean_host=$(echo "$host_name" | tr -d '\r' | xargs)
        [ -z "$clean_host" ] && continue
        if grep -xqF "$clean_host" "$LIST_FILE"; then
            echo "ℹ️  $clean_host already exists in list.txt — skipping" | tee -a "$LOG_FILE"
        else
            echo "$clean_host" >> "$LIST_FILE"
            echo "➕ Added $clean_host to list.txt" | tee -a "$LOG_FILE"
            NEW_LIST_ENTRIES=$((NEW_LIST_ENTRIES + 1))
        fi
    done
    sort_list_file "$LIST_FILE"
    echo "✅ list.txt updated safely (sorted)." | tee -a "$LOG_FILE"
}
update_hostgroups_file() {
    echo "📝 Updating Arabic section in hostgroups.txt..." | tee -a "$LOG_FILE"
    GROUPS_FILE="$HOSTS_DIR/hostgroups.txt"
    if [ -f "$GROUPS_FILE" ]; then
        backup_file "$GROUPS_FILE"
        for host_file in $NEW_HOSTS; do
            [ ! -f "$host_file" ] && continue
            full_name=$(basename "$host_file" .py)
            short_name=$(echo "$full_name" | sed 's/^host//')
            [ -z "$short_name" ] && continue
            if ! grep -q "\"$short_name\"" "$GROUPS_FILE"; then
                sed -i "/\"arabic\"[[:space:]]*:[[:space:]]*\[/a\  \"$short_name\"," "$GROUPS_FILE"
                echo "➕ Inserted \"$short_name\" under Arabic category" | tee -a "$LOG_FILE"
                NEW_HOSTGROUPS=$((NEW_HOSTGROUPS + 1))
            else
                echo "ℹ️  \"$short_name\" already exists in Arabic section" | tee -a "$LOG_FILE"
            fi
        done
        sort_arabic_group "$GROUPS_FILE"
        echo "✅ hostgroups.txt updated and sorted (Arabic section)." | tee -a "$LOG_FILE"
    else
        echo "⚠️  hostgroups.txt not found at: $GROUPS_FILE" | tee -a "$LOG_FILE"
    fi
}
# ===========================================================
# Cleanup Old Backups - Keep only latest backup
# ===========================================================
cleanup_old_backups() {
    echo "🧹 Cleaning up old backups (keeping only latest)..." | tee -a "$LOG_FILE"
    FILE_TYPES="aliases.txt list.txt hostgroups.txt hostlodynet.py"
    for file_type in $FILE_TYPES; do
        backups=$(find "$DEST_DIR" -name "$file_type.*.bak" | sort -r)
        backup_count=$(echo "$backups" | wc -l)
        if [ "$backup_count" -gt 1 ]; then
            echo "🔍 Found $backup_count backups for $file_type" | tee -a "$LOG_FILE"
            latest_backup=$(echo "$backups" | head -1)
            echo "💾 Keeping latest: $(basename "$latest_backup")" | tee -a "$LOG_FILE"
            echo "$backups" | tail -n +2 | while read -r old_backup; do
                if [ -f "$old_backup" ]; then
                    echo "  🗑️ Deleting: $(basename "$old_backup")" | tee -a "$LOG_FILE"
                    rm -f "$old_backup"
                fi
            done
        elif [ "$backup_count" -eq 1 ]; then
            echo "ℹ️  Only one backup found for $file_type - keeping it" | tee -a "$LOG_FILE"
        else
            echo "ℹ️  No backups found for $file_type" | tee -a "$LOG_FILE"
        fi
    done
    echo "🧹 Cleaning other old backups..." | tee -a "$LOG_FILE"
    find "$DEST_DIR" -name "*.bak" -mtime +7 | while read -r old_backup; do
        echo "  🗑️ Deleting old backup: $(basename "$old_backup")" | tee -a "$LOG_FILE"
        rm -f "$old_backup"
    done
}
# ===========================================================
# Cleanup Temporary Files
# ===========================================================
cleanup_temp_files() {
    echo "🧹 Cleaning up all temporary files..." | tee -a "$LOG_FILE"
    find /tmp -name "e2i_extract_*" -type d -mmin +60 2>/dev/null | while read -r temp_dir; do
        echo "  🗑️ Deleting old temp directory: $(basename "$temp_dir")" | tee -a "$LOG_FILE"
        rm -rf "$temp_dir"
    done
    find /tmp -name "My_e2iplayer_hosts.tar.gz" -mmin +60 2>/dev/null | while read -r temp_file; do
        echo "  🗑️ Deleting old temp file: $(basename "$temp_file")" | tee -a "$LOG_FILE"
        rm -f "$temp_file"
    done
    find /tmp -name "e2iplayer_*" -mmin +60 2>/dev/null | while read -r temp_file; do
        echo "  🗑️ Deleting old temp file: $(basename "$temp_file")" | tee -a "$LOG_FILE"
        rm -f "$temp_file"
    done
}
# ===========================================================
# Main Execution
# ===========================================================
main() {
    echo "🕒 Started at: $(date)" | tee -a "$LOG_FILE"
    cleanup_temp_files
    # ===========================================================
    # Download tar.gz directly
    # ===========================================================
    echo "> Downloading hosts archive directly..."
    wget -q --no-check-certificate "$REPO_URL" -O "$TAR_FILE"
    if [ ! -f "$TAR_FILE" ]; then
        echo "!! Failed to download the tar file. Check internet connection or URL." | tee -a "$LOG_FILE"
        exit 1
    fi
    echo "✅ Download completed: $(ls -lh "$TAR_FILE" | awk '{print $5}')" | tee -a "$LOG_FILE"
    # ===========================================================
    # Compare and extract
    # ===========================================================
    extract_and_compare_hosts
    # ===========================================================
    # Extract to system
    # ===========================================================
    echo "> Extracting to system..." | tee -a "$LOG_FILE"
    tar xzpf "$TAR_FILE" -C / >/dev/null 2>&1
    echo "✅ Extraction completed" | tee -a "$LOG_FILE"
    # ===========================================================
    # Update text files if there are new hosts
    # ===========================================================
    if [ $NEW_HOSTS_COUNT -gt 0 ]; then
        echo ""
        echo "> Updating text files with new hosts..." | tee -a "$LOG_FILE"
        update_aliases_file
        update_list_file
        update_hostgroups_file
    else
        echo ""
        echo "ℹ️  No new hosts found - skipping text file updates" | tee -a "$LOG_FILE"
    fi
    # ===========================================================
    # Cleanup
    # ===========================================================
    echo ""
    echo "> Performing cleanup..." | tee -a "$LOG_FILE"
    rm -f "$TAR_FILE"
    cleanup_old_backups
    cleanup_temp_files
    sync
    # ===========================================================
    # Final report
    # ===========================================================
    echo ""
    echo '************************************************************'
    echo "**               UPDATE COMPLETED SUCCESSFULLY           **"
    echo '************************************************************'
    echo "** 📦 New Host Files: $NEW_HOSTS_COUNT" | tee -a "$LOG_FILE"
    echo "** 📝 Text Updates: +$NEW_ALIASES aliases" | tee -a "$LOG_FILE"
    echo "**                 +$NEW_LIST_ENTRIES list entries" | tee -a "$LOG_FILE"
    echo "**                 +$NEW_HOSTGROUPS hostgroups" | tee -a "$LOG_FILE"
    echo "** 💾 Backups: Kept only latest backup" | tee -a "$LOG_FILE"
    echo "** 🧹 Cleanup: All temp files and old backups removed" | tee -a "$LOG_FILE"
    echo '************************************************************'
    echo "$(date): Updated $NEW_HOSTS_COUNT hosts, +$NEW_ALIASES aliases, +$NEW_LIST_ENTRIES list, +$NEW_HOSTGROUPS groups" >> "$LOG_FILE"
    sleep 2
    echo ""
    echo "🔄 Restarting Enigma2..." | tee -a "$LOG_FILE"
    killall -9 enigma2
    exit 0
}
# ===========================================================
# Script Entry Point
# ===========================================================
main