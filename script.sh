#!/bin/bash

WIDTH=60
BIN=$1
FUNC_LIST="$BIN.fun"
echo "Generating function list in $FUNC_LIST"

r2 -qq -c "aaaa; afl" "$BIN" > "$FUNC_LIST" 2>/dev/null

R2_CMDS="aaaa"
i=1
while read -r line; do
    func=$(echo "$line" | awk '{print $4}')
    cfg_file="$BIN-$i.cfg"
    R2_CMDS+="; pdfj @ $func > $cfg_file"
    i=$((i+1))
done < "$FUNC_LIST"

echo "Generating Control Flow Graphs for each function"
r2 -qq -c "$R2_CMDS" "$BIN" 2>/dev/null

rm -f $BIN.ss
rm -f $BIN.pdg

echo "Generating Safe Sets for each function"
TOTAL=$i
i=1
for func in $(awk '{print $4}' "$FUNC_LIST"); do
    
    python3 safe.py $BIN $BIN-$i.cfg
    rm $BIN-$i.cfg
    
    i=$((i+1))
    percent=$(( i * 100 / TOTAL ))
    filled=$(( i * WIDTH / TOTAL ))  
    empty=$(( WIDTH - filled ))
    bar=$(printf "%0.s#" $(seq 1 $filled))
    space=$(printf "%0.s." $(seq 1 $empty))

    # Print progress bar with carriage return
    printf "\rProgress : [%-${WIDTH}s] %3d%%" "$bar$space" "$percent"

done
echo
