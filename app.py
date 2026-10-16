import streamlit as st
from ask import answer, cited_ids, overlap_scores   # 沿用 ask.py 的 RAG 流程：檢索 Chroma → 組 prompt → 本地 LLM 回答

SUPPORT_THRESHOLD = 0.3   # 回答與段落的字面重疊度達到這個比例，就視為「回答主要依據的段落」

st.set_page_config(page_title="專案問答助理", page_icon="🔎")
st.title("專案問答助理（Local RAG）")
st.caption("bge-m3 embedding → Chroma（Top-4）→ Qwen2.5-3B（Ollama，本地 GPU）")

q = st.text_input("問一個關於我專案的問題")
if q:
    with st.spinner("檢索與生成中…"):
        text, hits = answer(q)
    st.markdown(text)

    used = cited_ids(text)
    scores = overlap_scores(text, hits)
    st.subheader("檢索到的段落")
    st.caption("✓ 回答有用 [編號] 引用｜★ 回答內容主要來自這段（依字面重疊度估計）｜% 為回答與該段的重疊度")
    for i, (h, s) in enumerate(zip(hits, scores), 1):
        m = h.metadata
        support = s >= SUPPORT_THRESHOLD and s == max(scores)
        mark = ("✓ " if i in used else "") + ("★ " if support else "")
        label = (f"{mark}[{i}] 重疊 {s:.0%}｜{m.get('project', m['source'])}"
                 f"｜Slide {m.get('slide', '?')}：{m.get('title', '')}")
        body = h.page_content.split("\n", 1)[-1]   # 第一行是 ingest.py 加的標頭，已顯示在標籤上
        with st.expander(label, expanded=(i in used) or support):
            st.text(body)
