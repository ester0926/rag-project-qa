"""看某個問題檢索到哪些 chunk、排第幾、距離多少（距離越小越相似）。
用法：python debug_retrieve.py "TAIDE 子 7 遇到什麼問題？怎麼解決？" [k=10] [chunk_size=500]"""
import sys
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

q = sys.argv[1]
k = int(sys.argv[2]) if len(sys.argv) > 2 else 10
size = sys.argv[3] if len(sys.argv) > 3 else "500"

db = Chroma(persist_directory=f"db_{size}",
            embedding_function=OllamaEmbeddings(model="bge-m3"),
            collection_name="projects")
for rank, (d, dist) in enumerate(db.similarity_search_with_score(q, k=k), 1):
    mark = "  ← ask.py 會用到" if rank <= 4 else ""
    print(f"#{rank}  距離={dist:.3f}  {d.metadata['source']}{mark}")
    print("    " + d.page_content[:150].replace("\n", " | "))
