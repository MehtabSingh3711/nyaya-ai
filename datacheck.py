from datasets import load_dataset
ds = load_dataset("mratanusarkar/Indian-Laws", split="train")

# Print all unique act titles
act_titles = set(ds["act_title"])
print(f"Total unique Acts: {len(act_titles)}")
print(f"Total sections: {len(ds)}")

# Check your key Acts are present
key_acts = ["Indian Contract Act", "MSME", "Information Technology", 
            "Indian Penal Code", "Code of Civil Procedure"]
for key in key_acts:
    matches = [t for t in act_titles if key.lower() in t.lower()]
    print(f"\n{key}: {matches}")

msme_matches = [t for t in act_titles if "micro" in t.lower() or "small" in t.lower() or "medium" in t.lower()]
print(msme_matches)