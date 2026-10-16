import re
import sys
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from opencc import OpenCC

to_tw = OpenCC("s2twp")   # 簡體 → 台灣繁體（含用語轉換），小模型常混入簡體字，這裡做最後保險

# 用法：python ask.py "問題" [chunk_size]，chunk_size 預設 500（對應 db_500）
DB_SIZE = sys.argv[2] if __name__ == "__main__" and len(sys.argv) > 2 else "500"

db = Chroma(
    persist_directory=f"db_{DB_SIZE}",
    embedding_function=OllamaEmbeddings(model="bge-m3"),
    collection_name="projects",
)
retriever = db.as_retriever(search_kwargs={"k": 4})
llm = ChatOllama(model="qwen2.5:3b", temperature=0.1)

PROMPT = """你是專案問答助理。只能根據下方「參考資料」回答；資料中沒有的內容請回答「資料中沒有提到」，不要猜測。

規則：
1. 每段參考資料開頭的 [專案｜Slide N：標題] 標示它屬於哪個專案、哪張投影片。
2. 問題如果指定了某個專案或子計畫（例如「子 7」），只能使用標題或內文明確屬於它的段落；其他子計畫的問題、數字、做法都不要混進答案。
3. 直接回答問題本身，不要重複問題，也不要照抄參考資料的投影片格式（例如「問題／角色／方法／結果／限制」）。
4. 一律使用繁體中文（台灣用語），不要使用簡體字。
5. 在句子後面用 [編號] 標出這句話來自哪段參考資料，例如「API 回傳含水量 31.5 [3]」；只標實際用到的段落。

參考資料：
{context}

問題：{question}"""

def answer(question: str):
    hits = retriever.invoke(question)
    context = "\n\n".join(
        f"[{i+1}] ({h.metadata['source']})\n{h.page_content}" for i, h in enumerate(hits)
    )
    reply = llm.invoke(PROMPT.format(context=context, question=question))
    text = to_tw.convert(reply.content).strip()
    # OpenCC 會把「为了解决」誤轉成「為瞭解決」（把「了解」當成一個詞），這裡改回來
    text = text.replace("為瞭解", "為了解")
    # 小模型有時還是會先重複一次問題（「問題：…」），這裡把開頭那行拿掉
    text = re.sub(r"^\s*問題[:：].*\n+", "", text)
    return text, hits


def cited_ids(text: str):
    """回答中用 [n] 引用到的段落編號，例如 {3}。"""
    return {int(n) for n in re.findall(r"\[(\d+)\]", text)}


def _bigrams(s: str):
    s = re.sub(r"\s+", "", s.lower())
    return {s[i:i + 2] for i in range(len(s) - 1)}


def overlap_scores(text: str, hits):
    """估計回答內容來自哪一段：回答的字元 bigram 有多少比例出現在該段（0～1）。
    3B 模型常不照指示標 [編號]，所以用字面重疊當備援；這是近似值，不是模型真正的引用。"""
    a = _bigrams(re.sub(r"\[\d+\]", "", text))
    if not a:
        return [0.0] * len(hits)
    return [len(a & _bigrams(h.page_content.split("\n", 1)[-1])) / len(a) for h in hits]

if __name__ == "__main__":
    text, hits = answer(sys.argv[1])
    print(f"（使用 db_{DB_SIZE}）")
    print(text)
    used = cited_ids(text)
    scores = overlap_scores(text, hits)
    print("\n檢索到的段落（✓＝回答有標 [編號] 引用；% ＝回答內容與該段的字面重疊度）：")
    for i, (h, s) in enumerate(zip(hits, scores), 1):
        m = h.metadata
        print(f"  {'✓' if i in used else ' '} [{i}] 重疊 {s:.0%}｜{m['source']}｜Slide {m.get('slide', '?')}：{m.get('title', '')}")
