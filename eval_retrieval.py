"""檢索評估：同時算「檔案層級」和「投影片層級」的 Hit@K。
用法：python eval_retrieval.py 300 500 800      （每個數字對應一個 db_<size> 索引）
- 檔案層級：top-K 裡有沒有正確的檔案（例如 docs/taide.md）
- 投影片層級：top-K 裡有沒有正確檔案中、題目標註的任一張投影片（questions.jsonl 的 slides）
  → 抓得到「同一個檔案、但撈到別張投影片」的錯誤，例如問子7 卻撈到子3
source 為 null 的題目（資料裡沒有答案）不計入命中率。"""
import json
import sys
from pathlib import Path
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

K = 4


def norm(path: str) -> str:
    return path.replace("\\", "/")


def evaluate(db, qs, k=K):
    file_hit = slide_hit = 0
    misses = []
    for item in qs:
        hits = db.similarity_search(item["q"], k=k)
        got = [(norm(d.metadata["source"]), d.metadata.get("slide")) for d in hits]
        f_ok = any(src == item["source"] for src, _ in got)
        s_ok = any(src == item["source"] and slide in item["slides"] for src, slide in got)
        file_hit += f_ok
        slide_hit += s_ok
        if not s_ok:
            misses.append((item, got, f_ok))
    return file_hit, slide_hit, misses


def short(src, slide):
    return f"{Path(src).stem}#{slide}" if slide is not None else Path(src).stem


if __name__ == "__main__":
    qs_all = [json.loads(l) for l in open("questions.jsonl", encoding="utf-8") if l.strip()]
    qs = [q for q in qs_all if q.get("source")]
    emb = OllamaEmbeddings(model="bge-m3")
    print(f"題數：{len(qs)}（另有 {len(qs_all) - len(qs)} 題資料中沒有答案，不計入）  K={K}\n")

    rows = []
    for size in sys.argv[1:] or ["500"]:
        if not Path(f"db_{size}").exists():   # 沒建索引時 Chroma 會開一個空庫，結果會默默變成 0%
            print(f"找不到 db_{size}，請先執行 python ingest.py {size}")
            continue
        db = Chroma(persist_directory=f"db_{size}", embedding_function=emb, collection_name="projects")
        f_hit, s_hit, misses = evaluate(db, qs)
        rows.append((size, f_hit, s_hit))
        print(f"=== chunk={size}：檔案層級 Hit@{K} = {f_hit}/{len(qs)} = {f_hit/len(qs):.0%}"
              f"｜投影片層級 Hit@{K} = {s_hit}/{len(qs)} = {s_hit/len(qs):.0%}")
        for item, got, f_ok in misses:
            kind = "檔案對、投影片錯" if f_ok else "檔案也錯"
            want = f"{Path(item['source']).stem}#{item['slides']}"
            print(f"  ✗ [{item['id']}] {kind}｜應為 {want}｜撈到 {', '.join(short(s, n) for s, n in got)}")
            print(f"      {item['q']}")
        print()

    if rows:
        print("| chunk size | 檔案層級 Hit@4 | 投影片層級 Hit@4 |")
        print("|---|---|---|")
        for size, f_hit, s_hit in rows:
            print(f"| {size} | {f_hit}/{len(qs)} ({f_hit/len(qs):.0%}) | {s_hit}/{len(qs)} ({s_hit/len(qs):.0%}) |")
