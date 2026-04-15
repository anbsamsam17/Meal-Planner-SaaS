"""Fix control characters in JSONB strings of migration SQL files.

Supabase/PostgreSQL JSONB parser rejects:
- Raw 0x0d (CR) characters
- \r escape sequences that produce 0x0d
- Unicode LINE SEPARATOR (U+2028) and PARAGRAPH SEPARATOR (U+2029)

This script cleans 03_recipes.sql by:
1. Replacing \r with empty (removes CR from recipe text)
2. Replacing \n with space (newlines in step text → spaces)
3. Removing U+2028/U+2029
"""

import sys

target = "scripts/migration/03_recipes.sql"

with open(target, "r", encoding="utf-8") as f:
    data = f.read()

original_len = len(data)

# Count before
backslash_r = data.count("\\r")
backslash_n = data.count("\\n")
u2028 = data.count("\u2028")
u2029 = data.count("\u2029")

print(f"AVANT nettoyage:")
print(f"  \\r : {backslash_r}")
print(f"  \\n : {backslash_n}")
print(f"  U+2028: {u2028}")
print(f"  U+2029: {u2029}")

# Fix: remove \r, replace \n with space, remove U+2028/U+2029
# Only within JSONB string values (between '[ and ]'::jsonb)
# But safer to just do it globally since \r and \n only appear in JSONB content

data = data.replace("\\r", "")
data = data.replace("\\n", " ")
data = data.replace("\u2028", " ")
data = data.replace("\u2029", " ")

# Count after
print(f"\nAPRES nettoyage:")
print(f"  \\r : {data.count(chr(92) + 'r')}")
print(f"  \\n : {data.count(chr(92) + 'n')}")
print(f"  U+2028: {data.count(chr(0x2028))}")
print(f"  Taille: {original_len} -> {len(data)} bytes")

with open(target, "w", encoding="utf-8", newline="\n") as f:
    f.write(data)

print(f"\nFichier {target} nettoyé avec succès.")
