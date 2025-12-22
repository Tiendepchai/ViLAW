import os, json
from shared.config import DATA_DIR

INP = os.path.join(DATA_DIR, "bo_pd_clean.jsonl")
OUT = os.path.join(DATA_DIR, "bo_pd_chunks.jsonl")

def to_chunks(text, max_len=1100, overlap=150):
    parts, cur = [], []
    length = 0
    for line in text.split("\n"):
        if length + len(line) + 1 > max_len and cur:
            parts.append("\n".join(cur))
            # overlap
            while cur and sum(len(x)+1 for x in cur) > overlap:
                length -= len(cur[0]) + 1
                cur = cur[1:]
        cur.append(line); length += len(line)+1
    if cur: parts.append("\n".join(cur))
    return parts

def run():
    cnt = 0
    with open(OUT, "w", encoding="utf-8") as w:
        for line in open(INP, encoding="utf-8"):
            d = json.loads(line)
            for i, chunk in enumerate(to_chunks(d["noi_dung"])):
                item = {**d, "chunk_id": f'{d["id"]}#c{i+1}', "text": chunk}
                w.write(json.dumps(item, ensure_ascii=False) + "\n")
                cnt += 1
    return {"chunk_jsonl": OUT, "chunks": cnt}

