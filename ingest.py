import re
import shutil
import sys
from pathlib import Path
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

CHUNK_SIZE = int(sys.argv[1]) if len(sys.argv) > 1 else 500
CHUNK_OVERLAP = CHUNK_SIZE // 10

# 每份文件對應的專案名稱，會寫進每個 chunk 的標頭（新增文件時在這裡補一行）
PROJECT_NAMES = {
    "thesis": "碩論專案（多模態 LLM 影片配樂推薦）",
    "taide": "TAIDE 專案（國科會農業 AI 計畫：神農 TAIDE 模型容器化與 API 交付驗證）",
    "emotion": "國科會情緒專案（學習情緒轉換與參與度的學習成效預測）",
    "aicup": "AI CUP 2024 競賽專案（太陽能發電量預測）",
}

SLIDE_RE = re.compile(r"^## Slide (\d+)\s*$", re.M)


def split_slides(text: str):
    """把 clean_docs.py 處理過的文件切成 [(投影片編號, 標題, 內容), ...]。"""
    parts = SLIDE_RE.split(text)
    # parts = [投影片前的文字, 編號1, 內容1, 編號2, 內容2, ...]
    slides = []
    if parts[0].strip():
        slides.append((0, "", parts[0].strip()))
    for num, body in zip(parts[1::2], parts[2::2]):
        body = body.strip()
        title = next((line.strip() for line in body.splitlines() if line.strip()), "")
        slides.append((int(num), title, body))
    return slides


def build_chunks(paths, chunk_size, chunk_overlap):
    """先按投影片切，再把每張投影片切成 chunk，並在每個 chunk 前加上「專案｜Slide N：標題」。
    投影片被切成好幾塊時，後面幾塊（例如備忘稿）也帶得到它屬於哪個專案、哪個主題，檢索才找得到。"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n### Notes:", "\n【若被追問】", "\n\n", "\n", "。", "，", " "],
    )
    chunks = []
    for p in paths:
        project = PROJECT_NAMES.get(p.stem, p.stem)
        text = p.read_text(encoding="utf-8")
        for num, title, body in split_slides(text):
            header = f"[{project}｜Slide {num}：{title}]" if num else f"[{project}]"
            for piece in splitter.split_text(body):
                chunks.append(Document(
                    page_content=f"{header}\n{piece}",
                    metadata={"source": str(p), "project": project, "slide": num, "title": title},
                ))
    return chunks


if __name__ == "__main__":
    paths = sorted(Path("docs").glob("*.md"))
    chunks = build_chunks(paths, CHUNK_SIZE, CHUNK_OVERLAP)
    print(f"{len(paths)} 份文件 → {len(chunks)} 個 chunks（size={CHUNK_SIZE}，每塊另加標頭）")

    # 重跑前先刪舊索引，否則 Chroma 會把同樣的 chunks 再加一次，檢索結果出現重複段落
    persist_dir = f"db_{CHUNK_SIZE}"
    shutil.rmtree(persist_dir, ignore_errors=True)

    Chroma.from_documents(
        chunks,
        embedding=OllamaEmbeddings(model="bge-m3"),
        persist_directory=persist_dir,
        collection_name="projects",
    )
