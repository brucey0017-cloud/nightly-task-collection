#!/bin/bash
# Test script for memory organizer tool

echo "=== Memory Organizer Tool Test ==="
echo "1. Generating summary:"
python3 memory_organizer.py summary | head -10

echo -e "\n2. Searching for 'commander':"
python3 memory_organizer.py search --query "commander" | head -5

echo -e "\n3. Testing mentions for commander user:"
python3 memory_organizer.py mentions --user-id "1470262775006625990"

echo -e "\n=== Test Complete ==="