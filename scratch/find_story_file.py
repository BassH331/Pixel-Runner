import json

log_path = "/home/chosen333/.gemini/antigravity/brain/e7f648b0-2b6f-4f47-80d2-cc91422d8e27/.system_generated/logs/overview.txt"

with open(log_path, "r", errors="ignore") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
matches = []

for line in lines:
    line = line.strip()
    if not line:
        continue
    try:
        data = json.loads(line)
        content = data.get("content", "")
        if "extracted_storyline.md" in content.lower():
            matches.append((data.get("step_index"), data.get("source"), content))
    except Exception as e:
        pass

print(f"Found {len(matches)} matches for extracted_storyline.md:")
for idx, source, content in matches:
    print(f"- Step {idx} ({source}) - Length: {len(content)}")
    print(f"  First line: {content.splitlines()[0] if content.splitlines() else ''}")
    print("-" * 50)
