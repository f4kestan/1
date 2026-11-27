# -*- coding: utf-8 -*-
"""清洗 PDF 提取的 txt，重新排版成可阅读的段落文本。

两类输入：
1. 正常类：PDF 文字层逐行提取，每行被原 PDF 换行硬断 → 合并段落 + 去页眉页脚 + 加缩进
2. 碎片类：竖排扫描件 OCR，逐字拆行且每字后带空格 → 去空格 + 合并 + 按句读断段

输出到 clean/ 目录，文件名与原名一致（便于 reader 直接换路径）。
"""
import os, re, glob, json, sys

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "text")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clean")

# 需剔除的水印/页眉/页脚行（整行匹配或子串匹配）
DROP_PATTERNS = [
    r"pdf\s*文件使用", r"pdffactory", r"fineprint", r"www\.fineprint",
    r"试用版本创建", r"^第\s*\d+\s*页", r"^\d{1,4}$",          # 纯数字页码
    r"^[\-\—\—\s]*\d+[\-\—\—\s]*$",                          # -123- 之类页码
]

def is_drop_line(s):
    s = s.strip()
    if not s:
        return True
    low = s.lower()
    for p in DROP_PATTERNS:
        if re.search(p, s, re.IGNORECASE) or re.search(p, low):
            return True
    return False

def clean_normal(text):
    """正常类：合并 PDF 硬换行成段落。"""
    raw_lines = text.split("\n")
    # 保留空行作为段落分隔符，去掉水印行
    lines = []
    for l in raw_lines:
        s = l.strip()
        if is_drop_line(s):
            lines.append("")       # 水印行变空行
        else:
            lines.append(s)
    paras = []
    buf = []
    def flush():
        if buf:
            p = "".join(buf)
            paras.append(p)
            buf.clear()
    for l in lines:
        if l == "":
            flush()
        else:
            buf.append(l)
    flush()
    return paras

def clean_fragmented(text):
    """碎片类：逐字拆行带空格，先拼成连续串再按句读断段。"""
    # 去掉所有空白，把逐字行拼回连续文本
    s = re.sub(r"\s+", "", text)
    # 按句末标点断句（保留标点），句号/问号/叹号/分号后断段
    # 用分组替换在标点后插入分隔
    parts = re.split(r"(?<=[。！？!?；;])", s)
    paras = []
    buf = ""
    for p in parts:
        buf += p
        # 累积到一定长度或遇到段落级标点就断段
        if len(buf) >= 80 or p.endswith("。") or p.endswith("！") or p.endswith("？"):
            if buf.strip():
                paras.append(buf)
                buf = ""
    if buf.strip():
        paras.append(buf)
    # 二次合并过短段落（可能是分号导致的碎段）
    merged = []
    for p in paras:
        if merged and len(merged[-1]) < 60:
            merged[-1] += p
        else:
            merged.append(p)
    return merged

def write_clean(name, paras):
    out = []
    for p in paras:
        # 段落首行缩进两个全角空格
        out.append("\u3000\u3000" + p)
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(out))
    return len(paras), sum(len(p) for p in paras)

def main():
    os.makedirs(OUT, exist_ok=True)
    files = sorted(glob.glob(os.path.join(SRC, "*.txt")))
    report = []
    for fp in files:
        name = os.path.basename(fp)
        text = open(fp, encoding="utf-8", errors="ignore").read()
        lines = [l for l in text.split("\n") if l.strip()]
        if not lines:
            continue
        avg = len(text) / len(lines)
        if avg < 10:   # 碎片类
            paras = clean_fragmented(text)
            kind = "碎片"
        else:
            paras = clean_normal(text)
            kind = "正常"
        n, chars = write_clean(name, paras)
        report.append((name, kind, n, chars))
    # 汇总
    print(f"{'文件':<32}{'类型':>6}{'段落数':>8}{'清洗后字数':>10}")
    for name, kind, n, chars in report:
        print(f"{name:<32}{kind:>6}{n:>8}{chars:>10}")

if __name__ == "__main__":
    main()
