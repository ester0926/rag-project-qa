"""清理 markitdown 轉出的 docs/*.md：刪圖片連結、投影片標記改成 ## 標題、合併多餘空行。
可重複執行（已清理過的檔案再跑一次結果不變）。"""
import re
from pathlib import Path

for p in sorted(Path("docs").glob("*.md")):
    t = p.read_text(encoding="utf-8").replace("\r\n", "\n")
    t = re.sub(r"^!\[[^\]]*\]\([^)]*\)\s*$\n?", "", t, flags=re.M)              # 圖片連結
    t = re.sub(r"^<!-- Slide number: (\d+) -->\s*$", r"## Slide \1", t, flags=re.M)  # 投影片邊界
    t = re.sub(r"\n{3,}", "\n\n", t).strip() + "\n"                               # 多餘空行
    p.write_text(t, encoding="utf-8", newline="\n")
    print(f"{p}: {len(t)} 字元, {t.count('## Slide')} 張投影片")
