# 知識庫文件（未公開）

這個資料夾放 RAG 的知識庫。原本的內容是我四個專案（碩論、國科會農業 AI 計畫、國科會學習情緒研究、AI CUP 2024）的 10 分鐘簡報與備忘稿，屬於個人資料，所以沒有上傳。

## 用自己的文件重現

1. 把簡報轉成 Markdown（一律用 `-o` 輸出，Windows 用 `>` 導向會存成 Big5 造成亂碼）：

   ```bash
   markitdown 你的簡報.pptx -o docs/myproject.md
   ```

2. 清理：刪圖片連結、把 `<!-- Slide number: N -->` 改成 `## Slide N`、合併空行。

   ```bash
   python clean_docs.py
   ```

3. 在 `ingest.py` 的 `PROJECT_NAMES` 補上檔名對應的專案名稱（會寫進每個 chunk 的標頭），再建索引：

   ```bash
   python ingest.py 500
   ```

4. 依自己的文件改寫 `questions.jsonl`（每題標註答案所在的檔案與投影片編號），再跑 `eval_retrieval.py`。

`ingest.py` 預期文件以 `## Slide N` 分段；其他格式的文件可以改 `split_slides()` 的切分規則。
