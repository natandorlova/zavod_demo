"""Validate the portable demo kit, not a generated exercise."""
from pathlib import Path
import json, hashlib, re, sys
ROOT=Path(__file__).resolve().parents[2]
kind="codex"
native=".agents" if kind=="codex" else ".claude"
required=["00_НАЧНИ_ЗДЕСЬ.md","AGENTS.md","roles/coordinator.md","system/delivery.md","system/live-demo.md","system/exercise-data.md","system/tools/check-exercise.py"]
required += ["roles/"+r+".md" for r in ["methodist","artist","assembler","controller"]]
required += ["input/01-phishing/"+f for f in ["brief.md","material.md","visual.md","interaction.md","assets/laptop.webp","assets/office.webp","references/README.md","references/manifest.json"]]
required += [prefix+s+"/SKILL.md" for prefix in ["skills/",native+"/skills/"] for s in ["zavod-design-exercise","zavod-review-options","zavod-check-exercise"]]
required += [(".codex/agents/zavod-"+r+".toml" if kind=="codex" else ".claude/agents/zavod-"+r+".md") for r in ["methodist","artist","assembler","controller"]]
if kind=="claude":required.append("CLAUDE.md")
errors=["Missing: "+f for f in required if not (ROOT/f).is_file() or (ROOT/f).stat().st_size==0]
refs=ROOT/"input/01-phishing/references"
for item in json.loads((refs/"manifest.json").read_text(encoding="utf-8"))["files"]:
    p=refs/item["file"]
    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=item["sha256"]:errors.append("Reference mismatch: "+item["file"])
for skill in ["zavod-design-exercise","zavod-review-options","zavod-check-exercise"]:
    p=ROOT/"skills"/skill/"SKILL.md"
    if "name: "+skill not in p.read_text(encoding="utf-8"):errors.append("Skill header: "+skill)
    wrapper=(ROOT/native/"skills"/skill/"SKILL.md").read_text(encoding="utf-8")
    if "skills/"+skill+"/SKILL.md" not in wrapper:errors.append("Skill entry: "+skill)
if kind=="codex":
    import tomllib
    for p in (ROOT/".codex/agents").glob("*.toml"):
        c=tomllib.loads(p.read_text(encoding="utf-8"))
        if not c.get("developer_instructions"):errors.append("Empty profile: "+p.name)
print("FAIL: " + "; ".join(errors) if errors else "PASS: portable layout, profiles, canonical skills, reference hashes; no prebuilt runs")
sys.exit(bool(errors))
