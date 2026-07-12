from datasets import load_dataset
ds = load_dataset("mratanusarkar/Indian-Laws", split="train")

it_act_sections = [r for r in ds if r["act_title"] == "Information Technology Act, 2000"]
print(f"IT Act sections found: {len(it_act_sections)}")

# The 2008 amendment added Section 66A, 69A, 43A among others
# Check if these post-amendment sections exist
section_numbers = [r["section"] for r in it_act_sections]
print("Sample sections:", section_numbers[:20])

# Look specifically for amendment-era sections
amendment_sections = ["43A", "66A", "66B", "66C", "66D", "66E", "66F", "69A", "69B"]
found = [s for s in amendment_sections if any(s in sec for sec in section_numbers)]
print(f"Post-2008-amendment sections found: {found}")