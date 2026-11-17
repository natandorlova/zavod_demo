"""Structural validator only. Python 3.11+, standard library. Never writes."""
import json
import re
import sys
from pathlib import Path

def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result

def validate(data):
    errors = []
    def fail(path, message):
        errors.append(f"{path}: {message}")
    def text_field(obj, key, path):
        value = obj.get(key)
        if not isinstance(value, str) or not value.strip():
            fail(f"{path}.{key}", "expected non-empty string")
            return None
        return value
    if not isinstance(data, dict):
        return ["root: expected object"]
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        fail("schema_version", "expected integer 1")
    for key in ("run_id", "version", "title", "context", "instruction"):
        text_field(data, key, "root")
    if isinstance(data.get("run_id"), str) and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", data["run_id"]):
        fail("run_id", "use lowercase letters, digits and hyphens")
    email = data.get("email")
    if not isinstance(email, dict):
        fail("email", "expected object")
        email = {}
    for key in ("sender_name", "sender_address", "recipient", "subject"):
        text_field(email, key, "email")
    blocks = email.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        fail("email.blocks", "expected non-empty array")
        blocks = []
    block_map = {}
    for i, block in enumerate(blocks):
        path = f"email.blocks[{i}]"
        if not isinstance(block, dict):
            fail(path, "expected object")
            continue
        ident = text_field(block, "id", path)
        text_field(block, "text", path)
        if ident is not None:
            if ident in block_map:
                fail(path, "duplicate block id")
            block_map[ident] = block
        if block.get("kind") not in ("paragraph", "link", "signature"):
            fail(path, "invalid kind")
        if "fragment_id" not in block:
            fail(path, "missing fragment_id (string or null)")
        elif block["fragment_id"] is not None and (not isinstance(block["fragment_id"], str) or not block["fragment_id"]):
            fail(path, "fragment_id must be non-empty string or null")
    fragments = data.get("fragments")
    if not isinstance(fragments, list):
        fail("fragments", "expected array")
        fragments = []
    if len(fragments) != 7:
        fail("fragments", "expected 7 fragments")
    fragment_map = {}
    used_locations = set()
    for i, frag in enumerate(fragments):
        path = f"fragments[{i}]"
        if not isinstance(frag, dict):
            fail(path, "expected object")
            continue
        ident = text_field(frag, "id", path)
        if ident is not None:
            if ident in fragment_map:
                fail(path, "duplicate fragment id")
            fragment_map[ident] = frag
        for key in ("evidence", "question", "takeaway"):
            text_field(frag, key, path)
        if type(frag.get("target")) is not bool:
            fail(path, "target must be boolean")
        loc = frag.get("location")
        if loc not in ("sender", "subject", "block"):
            fail(path, "invalid location")
        if loc in ("sender", "subject"):
            if loc in used_locations:
                fail(path, "duplicate header location")
            used_locations.add(loc)
            if "block_id" not in frag or frag["block_id"] is not None:
                fail(path, "header block_id must be null")
        if loc == "block":
            bid = frag.get("block_id")
            if not isinstance(bid, str) or bid not in block_map:
                fail(path, "block_id does not exist")
            elif block_map[bid].get("fragment_id") != ident:
                fail(path, "block link is not reciprocal")
        options = frag.get("options")
        if not isinstance(options, list):
            fail(path, "options must be array")
            options = []
        if len(options) != 3:
            fail(path, "expected 3 options")
        option_ids = set()
        correct_count = 0
        for j, option in enumerate(options):
            opath = f"{path}.options[{j}]"
            if not isinstance(option, dict):
                fail(opath, "expected object")
                continue
            oid = text_field(option, "id", opath)
            if oid is not None:
                if oid in option_ids:
                    fail(opath, "duplicate option id")
                option_ids.add(oid)
            text_field(option, "text", opath)
            text_field(option, "feedback", opath)
            if type(option.get("correct")) is not bool:
                fail(opath, "correct must be boolean")
            elif option["correct"]:
                correct_count += 1
        if correct_count != 1:
            fail(path, "expected exactly one correct option")
    if sum(isinstance(f, dict) and f.get("target") is True for f in fragments) != 4:
        fail("fragments", "expected 4 targets")
    if sum(isinstance(f, dict) and f.get("target") is False for f in fragments) != 3:
        fail("fragments", "expected 3 neutral fragments")
    for bid, block in block_map.items():
        fid = block.get("fragment_id")
        if fid is None:
            continue
        if not isinstance(fid, str) or fid not in fragment_map:
            fail(f"block {bid}", "fragment_id does not exist")
        else:
            frag = fragment_map[fid]
            if frag.get("location") != "block" or frag.get("block_id") != bid:
                fail(f"block {bid}", "fragment link is not reciprocal")
    summary = data.get("summary")
    if not isinstance(summary, dict):
        fail("summary", "expected object")
    else:
        for key in ("intro", "next_action"):
            text_field(summary, key, "summary")
        if "rewritten_email" in summary:
            text_field(summary, "rewritten_email", "summary")
    return errors

def main():
    if len(sys.argv) != 2:
        print("Usage: python system/tools/check-exercise.py path/to/exercise-vN.json")
        return 2
    try:
        data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"), object_pairs_hook=unique_object)
        errors = validate(data)
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    if errors:
        print("FAIL\n" + "\n".join(errors))
        return 1
    print("PASS: structure only; semantic and browser review still required.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
