"""Debug script to test the regex against sample act text."""
import re

SECTION_PATTERN = re.compile(
    r"^(\d+[A-Z]?)\.\s+(.+?)(?:[\.\u2014\-]|$)",
    re.MULTILINE,
)

SAMPLE_ACT = """THE INDIAN CONTRACT ACT, 1872

CHAPTER II

1. Short title.\u2014This Act may be called the Indian Contract Act, 1872. It extends to the whole of India except the State of Jammu and Kashmir.

2. Interpretation-clause.\u2014In this Act the following words and expressions are used in the following senses, unless a contrary intention appears from the context.

27. Agreements in restraint of trade void.\u2014Every agreement by which any one is restrained from exercising a lawful profession, trade or business of any kind, is to that extent void.

28. Agreements in restraint of legal proceedings void.\u2014Every agreement, by which any party thereto is restricted absolutely from enforcing his rights under or in respect of any contract, by the usual legal proceedings in the ordinary tribunals, is void.
"""

matches = list(SECTION_PATTERN.finditer(SAMPLE_ACT))
print(f"Found {len(matches)} matches:")
for m in matches:
    print(f"  Section {m.group(1)}: title='{m.group(2)}' at pos {m.start()}-{m.end()}")

# Also test what the actual test sees
print(f"\nRaw repr of line 84 area:")
lines = SAMPLE_ACT.split('\n')
for i, line in enumerate(lines):
    if line.strip():
        print(f"  Line {i}: {repr(line[:80])}")
