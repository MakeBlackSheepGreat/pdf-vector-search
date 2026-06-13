"""
PDF 文档结构分析器 — 语言无关的多策略检测

支持任意语言（中/英/日等）的 PDF 文档结构提取：
1. PDF 内嵌书签/大纲（最可靠）
2. TOC 目录页解析（通用）
3. 字号分析检测标题（语言无关的兜底）
4. 正则模式匹配（特定语言的补充）
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PageInfo:
    """单页的结构信息"""
    page_num: int = 0            # 1-based 页码
    chapter: str = ""            # 所属章节标题
    section: str = ""            # 所属节标题
    subsection: str = ""         # 所属小节标题
    page_type: str = "content"   # cover/toc/preface/content/appendix/index/bibliography/blank
    is_noise: bool = False       # 是否为噪声页（不参与正文搜索）
    heading_detected: str = ""   # 本页检测到的标题（如果有）
    heading_level: int = 0       # 标题层级（1=章, 2=节, 3=小节）


# ── 多语言噪声标题 ────────────────────────────────────────

_NOISE_PATTERNS = [
    # 英文
    (r"^table\s+of\s+contents$", "toc"),
    (r"^contents$", "toc"),
    (r"^index$", "index"),
    (r"^bibliography$", "bibliography"),
    (r"^references$", "bibliography"),
    (r"^appendix\s*[a-z]?\s*[:\.]", "appendix"),
    (r"^appendix\s+[a-z]$", "appendix"),
    (r"^preface$", "preface"),
    (r"^foreword$", "preface"),
    (r"^acknowledgments?$", "preface"),
    (r"^preamble$", "preface"),
    (r"^notation$", "preface"),
    # 中文
    (r"^目录$", "toc"),
    (r"^索引$", "index"),
    (r"^参考文献$", "bibliography"),
    (r"^附录", "appendix"),
    (r"^(前言|序言|序)$", "preface"),
    (r"^(导言|引言)$", "preface"),
    (r"^(后记|结语|总结)$", "appendix"),
    (r"^致谢$", "preface"),
    # 日文
    (r"^目次$", "toc"),
    # 通用：Supplementary Material
    (r"^supplementary\s+(material|data|information|table|figure)", "appendix"),
    (r"^(supporting\s+information|additional\s+file)", "appendix"),
]

_NOISE_RES = [(re.compile(p, re.IGNORECASE), t) for p, t in _NOISE_PATTERNS]


# ── 章节正则模式（多语言）────────────────────────────────

_CH_PATTERNS = [
    # 中文: 第一章、第二章、第1章
    re.compile(r"^第[一二三四五六七八九十百零\d]+[章篇部]\s*"),
    # 英文: "1. Title" / "2. Title"（顶级章节，数字+点+空格+大写字母）
    re.compile(r"^(\d{1,2})\.\s+[A-Z]"),
    # 英文罗马数字: "I. Title" / "IV. Title"
    re.compile(r"^(I{1,3}|IV|VI{0,3}|IX|XI{0,3})\.\s+[A-Z]"),
    # "Chapter 1" / "Part I"
    re.compile(r"^(Chapter|Part)\s+(\d+|[IVX]+)\b", re.IGNORECASE),
    # 学术论文顶级 section（无数字编号，直接标题）
    re.compile(r"^(Introduction|Materials?\s+and\s+Methods?|Methods?|Results|Discussion|"
               r"Conclusions?|Acknowledgments?|Funding|Data\s+Availability|"
               r"Author\s+Contributions?|Conflict\s+of\s+Interest|Ethics\s+Statement|"
               r"Supplementary\s+Material|Keywords?)\s*$", re.IGNORECASE),
    # 学术论文带编号的 section: "2. Materials and Methods", "3. Results"
    re.compile(r"^(\d{1,2})\.\s+(Introduction|Materials?\s+and\s+Methods?|Methods?|"
               r"Results|Discussion|Conclusions?|Related\s+Work|"
               r"Background|Proposed\s+Method|Experiments?|Evaluation)\b", re.IGNORECASE),
]

def _classify_noise_line(line: str) -> Optional[str]:
    """判断一行是否为噪声标题，返回页面类型或 None"""
    for pat, page_type in _NOISE_RES:
        if pat.match(line):
            return page_type
    return None


# ── 策略 1: PDF 书签提取 ──────────────────────────────────

def extract_bookmarks(pdf) -> List[Dict]:
    """从 PDF 内嵌书签/大纲提取结构

    Args:
        pdf: fitz.Document 对象

    Returns:
        [{"title": str, "page": int, "level": int}, ...]
    """
    toc = pdf.get_toc()
    if not toc:
        return []

    bookmarks = []
    for level, title, page_num in toc:
        title = title.strip()
        if not title:
            continue
        bookmarks.append({
            "title": title,
            "page": page_num,  # 1-based
            "level": level,
        })
    return bookmarks


def _bookmarks_to_pageinfo(bookmarks: List[Dict], total_pages: int) -> List[PageInfo]:
    """将书签列表转换为每页的 PageInfo

    书签给出的是起始页，需要向前传播到后续页面。
    跳过 page <= 0 的书签（如"第1部分"分隔符）。
    """
    # 过滤掉无效页码的书签
    bookmarks = [b for b in bookmarks if b["page"] > 0]

    pages = [PageInfo(page_num=i + 1) for i in range(total_pages)]

    # 预建 page -> bookmark 映射（O(1) 查找替代 O(n) 遍历）
    page_to_bm = {}
    for bm in bookmarks:
        p = bm["page"]
        if p not in page_to_bm:
            page_to_bm[p] = bm

    current = {0: "", 1: "", 2: "", 3: ""}
    bookmark_idx = 0

    for page_info in pages:
        pn = page_info.page_num
        while bookmark_idx < len(bookmarks) and bookmarks[bookmark_idx]["page"] <= pn:
            bm = bookmarks[bookmark_idx]
            level = bm["level"]
            current[level] = bm["title"]
            for l in range(level + 1, 4):
                current[l] = ""
            bookmark_idx += 1

        if current.get(1):
            page_info.chapter = current[1]
        if current.get(2):
            page_info.section = current[2]
        if current.get(3):
            page_info.subsection = current[3]

        bm = page_to_bm.get(pn)
        if bm:
            page_info.heading_detected = bm["title"]
            page_info.heading_level = bm["level"]

    return pages


# ── 策略 2: TOC 目录页解析 ────────────────────────────────

def parse_toc_from_text(pdf, max_toc_pages: int = 15) -> List[Dict]:
    """从 PDF 前几页解析目录，建立标题→页码映射

    Returns:
        [{"title": str, "page": int, "level": int}, ...]
    """
    # 先找到目录页的起始位置
    toc_start = -1
    for i in range(min(max_toc_pages, pdf.page_count)):
        text = pdf[i].get_text().strip()
        first_lines = "\n".join(text.split("\n")[:5]).lower()
        if ("table of contents" in first_lines or "contents" in first_lines
                or "目录" in first_lines or "目次" in first_lines):
            toc_start = i
            break

    if toc_start < 0:
        return []

    # 收集目录页文本（连续几页直到遇到正文）
    toc_text_parts = []
    for i in range(toc_start, min(toc_start + max_toc_pages, pdf.page_count)):
        text = pdf[i].get_text().strip()
        # 如果页面包含大量正文内容（> 500 字符且无页码引用），可能是目录结束
        lines = text.split("\n")
        has_page_refs = sum(1 for l in lines if re.search(r"\s+\d{1,3}\s*$", l)) > 3
        if not has_page_refs and i > toc_start and len(text) > 500:
            break
        toc_text_parts.append(text)

    toc_text = "\n".join(toc_text_parts)

    # 解析目录条目
    entries = []
    for line in toc_text.split("\n"):
        line = line.strip()
        if not line or len(line) < 3:
            continue

        # 匹配 "Title ... 123" 或 "Title  123" 格式
        m = re.match(r"^(.+?)\s*[.…]+\s*(\d{1,3})\s*$", line)
        if not m:
            m = re.match(r"^(.+?)\s{2,}(\d{1,3})\s*$", line)
        if not m:
            continue

        title = m.group(1).strip()
        page_num = int(m.group(2))

        # 判断层级（通过缩进或编号格式）
        level = 1
        if re.match(r"^\d+\.\d+\.\d+", title):
            level = 3
        elif re.match(r"^\d+\.\d+", title):
            level = 2
        elif re.match(r"^\d+\.", title):
            level = 1

        entries.append({"title": title, "page": page_num, "level": level})

    return entries


# ── 策略 3: 字号分析检测标题 ──────────────────────────────

def detect_headings_by_font(pdf, sample_pages: Optional[List[int]] = None,
                             max_pages: int = 50) -> List[PageInfo]:
    """通过字号分析检测每页的标题（语言无关）

    原理：标题字号 > 正文字号。通过统计全书字号分布，
    确定正文字号基线，然后检测每页的"超大字号"文本作为标题。

    Args:
        pdf: fitz.Document
        sample_pages: 指定采样页（默认均匀采样）
        max_pages: 最大采样页数

    Returns:
        List[PageInfo] 每页的结构信息
    """
    total = pdf.page_count

    # 第一遍：统计全书字号分布，确定正文字号
    size_freq = {}
    pages_to_scan = sample_pages or list(range(min(total, max_pages * 3)))

    for i in pages_to_scan:
        if i >= total:
            break
        try:
            blocks = pdf[i].get_text("dict")["blocks"]
        except Exception:
            continue
        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if text and len(text) > 1:
                        size = round(span["size"], 1)
                        size_freq[size] = size_freq.get(size, 0) + len(text)

    if not size_freq:
        return [PageInfo(page_num=i + 1) for i in range(total)]

    # 正文字号 = 出现频率最高的字号
    body_size = max(size_freq, key=size_freq.get)

    # 标题字号阈值：比正文大 15% 以上
    heading_threshold = body_size * 1.15
    # 大标题阈值：比正文大 30% 以上
    major_heading_threshold = body_size * 1.30

    # 第二遍：检测每页的标题
    pages = [PageInfo(page_num=i + 1) for i in range(total)]

    for i in range(total):
        try:
            blocks = pdf[i].get_text("dict")["blocks"]
        except Exception:
            continue

        page_headings = []  # (size, text, is_major)
        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                line_text_parts = []
                line_max_size = 0
                for span in line["spans"]:
                    text = span["text"].strip()
                    if text:
                        line_text_parts.append(text)
                        line_max_size = max(line_max_size, span["size"])

                if not line_text_parts:
                    continue
                line_text = " ".join(line_text_parts)

                # 只关注字号大于阈值的行
                if line_max_size >= heading_threshold and len(line_text) < 200:
                    is_major = line_max_size >= major_heading_threshold
                    page_headings.append((line_max_size, line_text, is_major))

        if page_headings:
            # 取字号最大的作为本页标题
            page_headings.sort(key=lambda x: -x[0])
            _, title_text, is_major = page_headings[0]
            pages[i].heading_detected = title_text
            pages[i].heading_level = 1 if is_major else 2

    return pages


# ── 策略 4: 噪声页面检测 ─────────────────────────────────

def detect_noise_pages(pdf, pages: List[PageInfo]) -> List[PageInfo]:
    """检测并标记噪声页面（语言无关）

    判断依据：
    1. 关键词匹配（多语言）
    2. 页面文本特征（目录页、索引页、参考文献页的统计特征）
    3. 空白/短文本页
    """
    total = pdf.page_count

    # 收集每页的文本特征
    for i in range(total):
        try:
            text = pdf[i].get_text().strip()
        except Exception:
            pages[i].is_noise = True
            pages[i].page_type = "blank"
            continue

        if len(text) < 30:
            pages[i].is_noise = True
            pages[i].page_type = "blank"
            continue

        lines = [l.strip() for l in text.split("\n") if l.strip()]

        # 关键词检测（前 5 行）
        for line in lines[:5]:
            noise_type = _classify_noise_line(line)
            if noise_type:
                pages[i].is_noise = True
                pages[i].page_type = noise_type
                break

        if pages[i].is_noise:
            continue

        # 统计特征检测
        if _is_toc_page(lines, text):
            pages[i].is_noise = True
            pages[i].page_type = "toc"
        elif _is_index_page(lines, text):
            pages[i].is_noise = True
            pages[i].page_type = "index"
        elif _is_bibliography_page(lines, text):
            pages[i].is_noise = True
            pages[i].page_type = "bibliography"

    return pages


def _is_toc_page(lines: list, text: str) -> bool:
    """目录页特征：大量短行 + 页码数字 + 有点号/省略号连接"""
    if len(lines) < 10:
        return False
    # 有页码引用的行比例
    page_ref_lines = sum(1 for l in lines if re.search(r"\s+\d{1,3}\s*$", l))
    ratio = page_ref_lines / len(lines)
    return ratio > 0.5 and len(text) < 3000


def _is_index_page(lines: list, text: str) -> bool:
    """索引页特征：字母排序的短词 + 页码，大量逗号分隔

    只在以下条件同时满足时才判定：
    1. 短行比例高
    2. 有字母排序特征（首字母按 A/B/C 排列）
    3. 有大量逗号分隔的引用格式
    4. 页面文本量适中（不是长篇正文）
    """
    if len(lines) < 15 or len(text) > 4000:
        return False
    # 短行比例高（< 60 字符），且行数多
    short_lines = sum(1 for l in lines if 5 < len(l) < 60)
    if short_lines / len(lines) < 0.7:
        return False
    # 有明确的字母排序特征：行首是单个英文字母 + 逗号/空格分隔
    alpha_ref_lines = sum(1 for l in lines if re.match(r"^[A-Z][\s,]", l))
    # 有大量逗号分隔（索引条目格式：keyword, 12, 45, 78）
    comma_lines = sum(1 for l in lines if l.count(",") >= 2)
    return (alpha_ref_lines / max(len(lines), 1) > 0.3 or
            comma_lines / max(len(lines), 1) > 0.4)


def _is_bibliography_page(lines: list, text: str) -> bool:
    """参考文献页特征：以 [数字] 或 Author (年份) 开头的引用格式

    严格判断：需要有大量标准引用格式的行。
    """
    if len(lines) < 8 or len(text) > 5000:
        return False
    # 标准引用格式：[1] Author, Title... 或 Author et al. (2020)
    ref_lines = sum(1 for l in lines if re.match(r"^\[\d{1,3}\]", l.strip()))
    author_year = sum(1 for l in lines if re.match(r"^\w+,\s+\w.*\(\d{4}\)", l.strip()))
    total_ref = ref_lines + author_year
    return total_ref / max(len(lines), 1) > 0.5


# ── 页眉页脚检测 ─────────────────────────────────────────

def detect_headers_footers(pdf, sample_size: int = 30) -> Tuple[set, set]:
    """检测页眉和页脚的重复文本

    支持两种检测方式：
    1. 精确匹配：完全相同的文本（如书名页脚）
    2. 模式匹配：格式相同但页码不同的文本（如 "Journal Name Page 3" vs "Journal Name Page 4"）

    Returns:
        (header_texts, footer_texts) — 需要从正文中去除的文本集合
    """
    header_candidates = {}  # normalized_pattern -> [original_texts]
    footer_candidates = {}

    def _normalize(text: str) -> str:
        """将文本中的数字替换为 #，用于模式匹配"""
        return re.sub(r"\d+", "#", text)

    step = max(1, pdf.page_count // sample_size)
    sampled = 0
    for i in range(0, min(pdf.page_count, sample_size * step), step):
        try:
            blocks = pdf[i].get_text("dict")["blocks"]
        except Exception:
            continue
        sampled += 1

        page_height = pdf[i].rect.height
        for block in blocks:
            if "lines" not in block:
                continue
            bbox = block["bbox"]
            for line in block["lines"]:
                text = " ".join(s["text"].strip() for s in line["spans"]).strip()
                if not text or len(text) > 120 or len(text) < 3:
                    continue
                y_top = bbox[1]
                y_bottom = bbox[3]

                # 页眉：页面顶部 12% 区域
                if y_top < page_height * 0.12:
                    pattern = _normalize(text)
                    if pattern not in header_candidates:
                        header_candidates[pattern] = {"texts": [], "count": 0}
                    header_candidates[pattern]["texts"].append(text)
                    header_candidates[pattern]["count"] += 1
                # 页脚：页面底部 10% 区域
                elif y_bottom > page_height * 0.90:
                    pattern = _normalize(text)
                    if pattern not in footer_candidates:
                        footer_candidates[pattern] = {"texts": [], "count": 0}
                    footer_candidates[pattern]["texts"].append(text)
                    footer_candidates[pattern]["count"] += 1

    # 只保留出现频率 > 30% 的模式
    threshold = max(sampled * 0.3, 2)
    headers = set()
    for pattern, info in header_candidates.items():
        if info["count"] >= threshold:
            # 添加所有该模式的原始文本变体
            for t in info["texts"]:
                headers.add(t)

    footers = set()
    for pattern, info in footer_candidates.items():
        if info["count"] >= threshold:
            for t in info["texts"]:
                footers.add(t)

    return headers, footers


# ── 主入口：综合结构分析 ──────────────────────────────────

def analyze_pdf_structure(pdf_path: str, pdf=None) -> Tuple[List[PageInfo], List[Dict]]:
    """分析 PDF 文档结构，返回每页信息和章节列表

    多策略融合：
    1. 优先使用 PDF 内嵌书签
    2. 其次解析 TOC 目录页
    3. 最后用字号分析兜底

    Args:
        pdf_path: PDF 文件路径
        pdf: 可选的已打开 fitz.Document 对象（避免重复打开）

    Returns:
        (pages, chapters)
        pages: List[PageInfo] — 每页的结构信息
        chapters: List[Dict] — 章节列表 [{"title": str, "page": int, "level": int}]
    """
    import fitz
    close_pdf = pdf is None
    if pdf is None:
        pdf = fitz.open(pdf_path)
    total = pdf.page_count

    # 策略 1: PDF 书签
    bookmarks = extract_bookmarks(pdf)
    if bookmarks and len(bookmarks) >= 3:
        pages = _bookmarks_to_pageinfo(bookmarks, total)
        # 用书签作为章节列表
        chapters = [b for b in bookmarks if b["level"] <= 2 and b["page"] > 0]
    else:
        # 策略 2: TOC 解析
        toc_entries = parse_toc_from_text(pdf)
        if toc_entries and len(toc_entries) >= 3:
            pages = _bookmarks_to_pageinfo(toc_entries, total)
            chapters = toc_entries
        else:
            # 策略 3: 字号分析
            font_pages = detect_headings_by_font(pdf)
            pages = font_pages
            # 从字号分析结果提取章节列表
            chapters = []
            for p in pages:
                if p.heading_detected and p.heading_level <= 2:
                    chapters.append({
                        "title": p.heading_detected,
                        "page": p.page_num,
                        "level": p.heading_level,
                    })
            # 传播章节信息到后续页面
            current = {0: "", 1: "", 2: ""}
            for p in pages:
                if p.heading_detected and p.heading_level > 0:
                    level = min(p.heading_level, 3)
                    current[level - 1] = p.heading_detected
                    for l in range(level, 3):
                        if l > level - 1:
                            current[l] = ""
                p.chapter = current.get(0, "")
                p.section = current.get(1, "")
                p.subsection = current.get(2, "")

    # 噪声检测
    pages = detect_noise_pages(pdf, pages)

    if close_pdf:
        pdf.close()
    return pages, chapters


def get_chapter_tree(chapters: List[Dict]) -> str:
    """将章节列表格式化为树形字符串"""
    lines = []
    for ch in chapters:
        indent = "  " * (ch["level"] - 1)
        lines.append(f"{indent}{ch['title']} (p{ch['page']})")
    return "\n".join(lines)


# ── 多栏布局检测和文本提取 ────────────────────────────────

def extract_page_text(pdf, page_idx: int, remove_headers: set = None,
                       remove_footers: set = None) -> str:
    """提取单页文本，自动处理多栏布局和页眉页脚

    Args:
        pdf: fitz.Document
        page_idx: 0-based 页码
        remove_headers: 需要去除的页眉文本集合
        remove_footers: 需要去除的页脚文本集合

    Returns:
        处理后的页面文本
    """
    try:
        blocks = pdf[page_idx].get_text("dict")["blocks"]
    except Exception:
        return ""

    page_width = pdf[page_idx].rect.width
    page_height = pdf[page_idx].rect.height

    # 分离文本块和图片块
    text_blocks = []
    for block in blocks:
        if "lines" not in block:
            continue
        bbox = block["bbox"]
        # 跳过页眉区域（顶部 10%）和页脚区域（底部 8%）的块
        if bbox[1] < page_height * 0.10 or bbox[3] > page_height * 0.92:
            # 但如果块跨越了页眉/页脚区域（如正文块），不排除
            block_height = bbox[3] - bbox[1]
            if block_height < page_height * 0.08:
                continue  # 小块在页眉/页脚区域，跳过

        # 提取块的文本
        lines_text = []
        for line in block["lines"]:
            line_text = " ".join(s["text"].strip() for s in line["spans"]).strip()
            if line_text:
                lines_text.append(line_text)

        if lines_text:
            text_blocks.append({
                "bbox": bbox,
                "text": "\n".join(lines_text),
                "x_center": (bbox[0] + bbox[2]) / 2,
                "y_top": bbox[1],
            })

    if not text_blocks:
        return ""

    # 检测是否为多栏布局
    is_multicolumn = _detect_multicolumn(text_blocks, page_width)

    if is_multicolumn:
        # 多栏：先左栏后右栏，每栏内按 y 坐标排序
        mid_x = page_width / 2
        left_blocks = [b for b in text_blocks if b["x_center"] < mid_x]
        right_blocks = [b for b in text_blocks if b["x_center"] >= mid_x]
        left_blocks.sort(key=lambda b: b["y_top"])
        right_blocks.sort(key=lambda b: b["y_top"])
        ordered = left_blocks + right_blocks
    else:
        # 单栏：按 y 坐标排序
        text_blocks.sort(key=lambda b: b["y_top"])
        ordered = text_blocks

    # 合并文本
    text = "\n".join(b["text"] for b in ordered)

    # 去除页眉页脚文本
    if remove_headers:
        for hf in remove_headers:
            text = text.replace(hf, "")
    if remove_footers:
        for hf in remove_footers:
            text = text.replace(hf, "")

    return text.strip()


def _detect_multicolumn(text_blocks: list, page_width: float) -> bool:
    """检测页面是否为多栏布局

    原理：如果页面有大量文本块的 x 中心在左半边，
    同时也有大量在右半边，则认为是多栏。
    """
    if len(text_blocks) < 6:
        return False

    mid_x = page_width / 2
    left_count = sum(1 for b in text_blocks if b["x_center"] < mid_x * 0.85)
    right_count = sum(1 for b in text_blocks if b["x_center"] > mid_x * 1.15)

    # 左右两边都有足够多的块，且比例接近
    total = len(text_blocks)
    if left_count > total * 0.25 and right_count > total * 0.25:
        return True
    return False
