import hashlib
import json


def context_hash(context: dict) -> str:
    encoded = json.dumps(context, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
