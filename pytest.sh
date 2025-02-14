#!/bin/bash
# Ensure inotifywait is installed (usually via inotify-tools on Linux)
# For example, on Debian/Ubuntu: sudo apt-get install inotify-tools

WATCH_FILES="$@"

while true; do
    inotifywait -e modify $WATCH_FILES
    clear
    # -s: show output of "print()" statements
    # -v: show executed test names
    pytest -s -v
done
