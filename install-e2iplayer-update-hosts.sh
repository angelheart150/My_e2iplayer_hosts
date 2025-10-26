#!/bin/sh
##############################################################
# E2IPlayer Hosts Auto Updater by Mohamed Elsafty
# Version: 3.6 (Optimized Timing)
# Description: Direct download and smart update of E2IPlayer hosts
# Features: Auto backup, text file merging, cleanup, and validation
##############################################################
#setup command=wget -q "--no-check-certificate" https://github.com/angelheart150/My_e2iplayer_hosts/raw/main/install-e2iplayer-update-hosts.sh -O - | /bin/sh
##############################################################
echo ''
echo '************************************************************'
echo '**         E2IPlayer Hosts Update Script                  **'
echo '************************************************************'
echo '**         Uploaded by: Mohamed Elsafty                   **'
echo '************************************************************'
sleep 1
# ===========================================================
# Configuration Variables
# ===========================================================
DEST_DIR="/usr/lib/enigma2/python/Plugins/Extensions/IPTVPlayer"
HOSTS_DIR="$DEST_DIR/hosts"
TAR_FILE="/tmp/My_e2iplayer_hosts.tar.gz"
REPO_URL="https://github.com/angelheart150/My_e2iplayer_hosts/raw/main/My_e2iplayer_hosts.tar.gz"
DATE=$(date +%Y%m%d)
LOG_FILE="/tmp/e2iplayer_update.log"
# Counters for tracking updates
NEW_HOSTS_COUNT=0
NEW_ALIASES=0
NEW_LIST_ENTRIES=0
NEW_HOSTGROUPS=0
# ===========================================================
# Utility Functions
# ===========================================================
# Backup file with date stamp
backup_file() {
    local file="$1"
    if [ -f "$file" ]; then
        local backup="${file}.${DATE}.bak"
        cp -f "$file" "$backup"
        echo "📦 Backed up: $(basename "$file") → $(basename "$backup")" | tee -a "$LOG_FILE"
    fi
}
# Normalize file formatting (CRLF to LF, trim spaces, ensure newline)
normalize_file() {
    f="$1"
    [ -f "$f" ] || return
    sed -i 's/\r$//' "$f"
    sed -i 's/[[:space:]]\+$//' "$f"
    sed -i '/./,$!d' "$f"
    sed -i -e '$a\' "$f"
}
# Sort list file alphabetically and remove duplicates
sort_list_file() {
    f="$1"
    normalize_file "$f"
    grep -v '^[[:space:]]*$' "$f" | sort -u > "${f}.tmp"
    mv "${f}.tmp" "$f"
    sed -i '/^[[:space:]]*$/d' "$f"
    sed -i '/./,$!d' "$f"
}
# Sort aliases file while preserving dictionary structure
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
# Sort Arabic group in hostgroups file alphabetically
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
# Extract host name and URL from Python host file
extract_host_info() {
    local host_file="$1"
    local host_info=""
    # Extract host name from filename (without .py)
    local host_name=$(basename "$host_file" .py)
    # Extract URL from gettytul function
    local host_url=$(grep "def gettytul()" "$host_file" -A 1 | grep "return" | head -1 | sed "s/.*return[[:space:]]*['\"]\([^'\"]*\)['\"].*/\1/")
    # If URL not found, use host name as default
    if [ -z "$host_url" ]; then
        host_url="https://${host_name}.com"
    fi
    echo "$host_name|$host_url"
}
# ===========================================================
# Check if host needs to be added to text files
# ===========================================================
# Verify if host exists in all text files
check_host_in_text_files() {
    local host_name="$1"
    local short_name="$2"
    # Check if host exists in list.txt
    if ! grep -xqF "$host_name" "$HOSTS_DIR/list.txt" 2>/dev/null; then
        return 0  # Host not found - needs addition
    fi
    # Check if host exists in hostgroups.txt
    if ! grep -q "\"$short_name\"" "$HOSTS_DIR/hostgroups.txt" 2>/dev/null; then
        return 0  # Host not found - needs addition
    fi
    # Check if host exists in aliases.txt
    if ! grep -q "'$host_name':" "$HOSTS_DIR/aliases.txt" 2>/dev/null; then
        return 0  # Host not found - needs addition
    fi
    return 1  # Host exists in all files
}
# ===========================================================
# Extract and Compare Host Files
# ===========================================================
# Extract archive and compare with existing files
extract_and_compare_hosts() {
    echo "🔍 Extracting and comparing host files..." | tee -a "$LOG_FILE"
    # Extract archive to temporary directory for comparison
    TEMP_EXTRACT="/tmp/e2i_extract_$$"
    mkdir -p "$TEMP_EXTRACT"
    tar xzpf "$TAR_FILE" -C "$TEMP_EXTRACT" >/dev/null 2>&1
    # File to store new host names
    NEW_HOSTS_FILE="/tmp/new_hosts_$$.txt"
    > "$NEW_HOSTS_FILE"
    # File to store host information
    HOST_INFO_FILE="/tmp/host_info_$$.txt"
    > "$HOST_INFO_FILE"
    # Search for host files in archive
    for host_file in "$TEMP_EXTRACT"/usr/lib/enigma2/python/Plugins/Extensions/IPTVPlayer/hosts/host*.py; do
        [ -f "$host_file" ] || continue
        filename=$(basename "$host_file")
        host_name=$(basename "$host_file" .py)
        short_name=$(echo "$host_name" | sed 's/^host//')
        echo "🔍 Checking: $filename" | tee -a "$LOG_FILE"
        # Check if host needs to be added to text files
        if check_host_in_text_files "$host_name" "$short_name"; then
            # Host not found in text files - add it
            echo "$filename" >> "$NEW_HOSTS_FILE"
            NEW_HOSTS_COUNT=$((NEW_HOSTS_COUNT + 1))
            # Extract host information and save it
            host_info=$(extract_host_info "$host_file")
            echo "$host_info" >> "$HOST_INFO_FILE"
            echo "🆕 Host needs text file updates: $filename" | tee -a "$LOG_FILE"
        else
            echo "ℹ️  Host already in text files: $filename" | tee -a "$LOG_FILE"
        fi
        # Check if file exists in system
        dest_file="$HOSTS_DIR/$filename"
        if [ ! -f "$dest_file" ]; then
            echo "📦 New file will be installed: $filename" | tee -a "$LOG_FILE"
        elif ! cmp -s "$host_file" "$dest_file"; then
            backup_file "$dest_file"
            echo "🔄 File will be updated: $filename" | tee -a "$LOG_FILE"
        fi
    done
    # Clean temporary extraction folder immediately after use
    echo "🧹 Cleaning temporary extraction folder..." | tee -a "$LOG_FILE"
    rm -rf "$TEMP_EXTRACT"
    echo "✅ Comparison completed - $NEW_HOSTS_COUNT host(s) need text file updates" | tee -a "$LOG_FILE"
}
# ===========================================================
# Update Text Files
# ===========================================================
# Update aliases.txt with new host entries
update_aliases_file() {
    echo "📝 Updating aliases.txt..." | tee -a "$LOG_FILE"
    ALIASES_FILE="$HOSTS_DIR/aliases.txt"
    backup_file "$ALIASES_FILE"
    if [ -f "/tmp/host_info_$$.txt" ] && [ -s "/tmp/host_info_$$.txt" ]; then
        while IFS='|' read -r host_name host_url; do
            [ -z "$host_name" ] && continue
            # Create new entry
            formatted="'$host_name': '$host_url',"
            if ! grep -q "'$host_name':" "$ALIASES_FILE"; then
                sed -i "/^{/a $formatted" "$ALIASES_FILE"
                echo "➕ Added alias: $formatted" | tee -a "$LOG_FILE"
                NEW_ALIASES=$((NEW_ALIASES + 1))
            else
                echo "ℹ️  Alias for $host_name already exists" | tee -a "$LOG_FILE"
            fi
        done < "/tmp/host_info_$$.txt"
    else
        echo "ℹ️  No host information found for aliases update" | tee -a "$LOG_FILE"
    fi
    sort_aliases_file "$ALIASES_FILE"
    echo "✅ aliases.txt updated." | tee -a "$LOG_FILE"
}
# Update list.txt with new host entries
update_list_file() {
    echo "📝 Updating list.txt..." | tee -a "$LOG_FILE"
    LIST_FILE="$HOSTS_DIR/list.txt"
    backup_file "$LIST_FILE"
    normalize_file "$LIST_FILE"
    if [ -f "/tmp/new_hosts_$$.txt" ] && [ -s "/tmp/new_hosts_$$.txt" ]; then
        while read -r filename; do
            [ -z "$filename" ] && continue
            # Extract host name from filename
            host_name=$(basename "$filename" .py)
            clean_host=$(echo "$host_name" | tr -d '\r' | xargs)
            [ -z "$clean_host" ] && continue
            if grep -xqF "$clean_host" "$LIST_FILE"; then
                echo "ℹ️  $clean_host already exists in list.txt — skipping" | tee -a "$LOG_FILE"
            else
                echo "$clean_host" >> "$LIST_FILE"
                echo "➕ Added $clean_host to list.txt" | tee -a "$LOG_FILE"
                NEW_LIST_ENTRIES=$((NEW_LIST_ENTRIES + 1))
            fi
        done < "/tmp/new_hosts_$$.txt"
    else
        echo "ℹ️  No new hosts found for list update" | tee -a "$LOG_FILE"
    fi
    sort_list_file "$LIST_FILE"
    echo "✅ list.txt updated safely (sorted)." | tee -a "$LOG_FILE"
}
# Update Arabic section in hostgroups.txt
update_hostgroups_file() {
    echo "📝 Updating Arabic section in hostgroups.txt..." | tee -a "$LOG_FILE"
    GROUPS_FILE="$HOSTS_DIR/hostgroups.txt"
    if [ -f "$GROUPS_FILE" ]; then
        backup_file "$GROUPS_FILE"
        if [ -f "/tmp/new_hosts_$$.txt" ] && [ -s "/tmp/new_hosts_$$.txt" ]; then
            while read -r filename; do
                [ -z "$filename" ] && continue
                # Extract short name (without "host")
                full_name=$(basename "$filename" .py)
                short_name=$(echo "$full_name" | sed 's/^host//')
                [ -z "$short_name" ] && continue
                if ! grep -q "\"$short_name\"" "$GROUPS_FILE"; then
                    # Add short name to Arabic section
                    sed -i "/\"arabic\"[[:space:]]*:[[:space:]]*\[/a\  \"$short_name\"," "$GROUPS_FILE"
                    echo "➕ Inserted \"$short_name\" under Arabic category" | tee -a "$LOG_FILE"
                    NEW_HOSTGROUPS=$((NEW_HOSTGROUPS + 1))
                else
                    echo "ℹ️  \"$short_name\" already exists in Arabic section" | tee -a "$LOG_FILE"
                fi
            done < "/tmp/new_hosts_$$.txt"
        else
            echo "ℹ️  No new hosts found for hostgroups update" | tee -a "$LOG_FILE"
        fi
        sort_arabic_group "$GROUPS_FILE"
        echo "✅ hostgroups.txt updated and sorted (Arabic section)." | tee -a "$LOG_FILE"
    else
        echo "⚠️  hostgroups.txt not found at: $GROUPS_FILE" | tee -a "$LOG_FILE"
    fi
}
# ===========================================================
# Cleanup Temporary Files
# ===========================================================
# Clean up all temporary files and directories
cleanup_temp_files() {
    echo "🧹 Cleaning up all temporary files..." | tee -a "$LOG_FILE"
    # Clean current script temporary files
    rm -f "/tmp/new_hosts_$$.txt" 2>/dev/null
    rm -f "/tmp/host_info_$$.txt" 2>/dev/null
    rm -f "$TAR_FILE" 2>/dev/null
    # Clean old temporary directories
    find /tmp -name "e2i_extract_*" -type d -mmin +60 2>/dev/null | while read -r temp_dir; do
        echo "  🗑️ Deleting old temp directory: $(basename "$temp_dir")" | tee -a "$LOG_FILE"
        rm -rf "$temp_dir"
    done
}
# ===========================================================
# Main Execution
# ===========================================================
main() {
    echo "🕒 Started at: $(date)" | tee -a "$LOG_FILE"
    # Clean old temporary files before starting
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
    sleep 0.3
    # ===========================================================
    # Compare and extract
    # ===========================================================
    extract_and_compare_hosts
    sleep 0.5
    # ===========================================================
    # Extract to system
    # ===========================================================
    echo "> Extracting to system..." | tee -a "$LOG_FILE"
    tar xzpf "$TAR_FILE" -C / >/dev/null 2>&1
    echo "✅ Extraction completed" | tee -a "$LOG_FILE"
    sleep 0.3
    # ===========================================================
    # Update text files if there are new hosts
    # ===========================================================
    if [ $NEW_HOSTS_COUNT -gt 0 ]; then
        echo ""
        echo "> Updating text files with $NEW_HOSTS_COUNT host(s)..." | tee -a "$LOG_FILE"
        sleep 0.5
        update_aliases_file
        sleep 0.3
        update_list_file
        sleep 0.3
        update_hostgroups_file
        sleep 0.5
    else
        echo ""
        echo "ℹ️  No new hosts found - skipping text file updates" | tee -a "$LOG_FILE"
        sleep 0.5
    fi
    # ===========================================================
    # Cleanup
    # ===========================================================
    echo ""
    echo "> Performing cleanup..." | tee -a "$LOG_FILE"
    cleanup_temp_files
    sync
    sleep 0.5
    # ===========================================================
    # Final report
    # ===========================================================
    echo ""
    echo '************************************************************'
    echo "**               UPDATE COMPLETED SUCCESSFULLY           **"
    echo '************************************************************'
    echo "** 📦 Hosts needing text updates: $NEW_HOSTS_COUNT" | tee -a "$LOG_FILE"
    echo "** 📝 Text Updates: +$NEW_ALIASES aliases" | tee -a "$LOG_FILE"
    echo "**                 +$NEW_LIST_ENTRIES list entries" | tee -a "$LOG_FILE"
    echo "**                 +$NEW_HOSTGROUPS hostgroups" | tee -a "$LOG_FILE"
    echo "** 🧹 Cleanup: All temp files removed" | tee -a "$LOG_FILE"
    echo '************************************************************'
    echo "$(date): $NEW_HOSTS_COUNT hosts needed updates, +$NEW_ALIASES aliases, +$NEW_LIST_ENTRIES list, +$NEW_HOSTGROUPS groups" >> "$LOG_FILE"
    sleep 3
    echo ""
    echo "🔄 Restarting Enigma2..." | tee -a "$LOG_FILE"
    sleep 1
    killall -9 enigma2
    exit 0
}
# ===========================================================
# Script Entry Point
# ===========================================================
main