"""
PDF 向量搜索核心库

提供 PDFVectorSearch 类，支持:
- 加载 PDF 文件（任意语言），自动提取章节结构
- 构建 ChromaDB 向量索引（含结构化 metadata）
- 语义搜索查询（支持按章节/页码过滤）
- 增量添加 PDF
- 管理多个集合
"""

import os
from typing import List, Optional, Dict, Any

import chromadb
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.schema import Document

from config import Config, get_config
from embedder import SiliconFlowEmbedding
from pdf_structure import analyze_pdf_structure, detect_headers_footers, extract_page_text, PageInfo


class PDFVectorSearch:
    """PDF 向量搜索引擎

    用法:
        from config import get_config
        from vector_search import PDFVectorSearch

        cfg = get_config(pdf_path="book.pdf")
        searcher = PDFVectorSearch(cfg)
        searcher.ingest()            # 加载 PDF + 构建索引
        result = searcher.search("你的问题")
    """

    def __init__(self, config: Optional[Config] = None, **kwargs):
        """
        Args:
            config: Config 对象。如果为 None，会通过 get_config(**kwargs) 自动创建。
            **kwargs: 传递给 get_config 的覆盖参数。
        """
        if config is None:
            config = get_config(**kwargs)
        self.config = config
        self._setup_models()
        self._setup_chromadb()

    def _setup_models(self):
        """初始化嵌入模型和全局设置"""
        self.embed_model = SiliconFlowEmbedding(
            api_key=self.config.api_key,
            model_name=self.config.embedding_model,
            api_base=self.config.api_base,
        )
        Settings.embed_model = self.embed_model
        Settings.chunk_size = self.config.chunk_size
        Settings.chunk_overlap = self.config.chunk_overlap

    def _setup_chromadb(self):
        """初始化 ChromaDB 客户端"""
        db_path = self.config.db_path
        os.makedirs(db_path, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path=db_path)
        self.vector_store = None
        self.index = None

    def _resolve_pdf_path(self, pdf_path: Optional[str] = None) -> str:
        """解析 PDF 路径，检查文件存在性"""
        path = pdf_path or self.config.pdf_path
        if not path or not os.path.exists(path):
            raise FileNotFoundError(f"PDF 文件不存在: {path}")
        return path

    # ── PDF 加载 ──────────────────────────────────────────────

    def load_pdf(self, pdf_path: Optional[str] = None,
                 min_text_length: int = 30) -> List[Document]:
        """加载 PDF 文件，自动提取多语言章节结构

        Args:
            pdf_path: PDF 文件路径。如果为 None，使用 config.pdf_path。
            min_text_length: 最小文本长度，低于此值的页面被跳过

        Returns:
            LlamaIndex Document 列表（按页，含结构化 metadata）
        """
        import fitz

        path = self._resolve_pdf_path(pdf_path)
        print(f"📄 加载 PDF: {path}")

        # 多策略结构分析
        page_infos, chapters = analyze_pdf_structure(path)
        if chapters:
            print(f"📖 检测到 {len(chapters)} 个章节")
            for ch in chapters[:5]:
                print(f"    {ch['title'][:50]} (p{ch['page']})")
            if len(chapters) > 5:
                print(f"    ... 共 {len(chapters)} 个")

        # 检测页眉页脚
        pdf = fitz.open(path)
        headers, footers = detect_headers_footers(pdf)
        if headers or footers:
            print(f"  检测到 {len(headers)} 个页眉、{len(footers)} 个页脚，自动去除")

        # 逐页提取文本并组装 Document（支持多栏布局）
        documents = []
        skipped = 0
        noise_count = 0

        for i in range(pdf.page_count):
            # 使用 extract_page_text 处理多栏布局和页眉页脚
            text = extract_page_text(pdf, i, remove_headers=headers, remove_footers=footers)
            if len(text) < min_text_length:
                skipped += 1
                continue

            # 获取本页结构信息
            info = page_infos[i] if i < len(page_infos) else PageInfo(page_num=i + 1)

            metadata = {
                "page": str(i + 1),
                "source": path,
                "chapter": info.chapter,
                "section": info.section,
                "subsection": info.subsection,
                "page_type": info.page_type,
                "is_noise": "true" if info.is_noise else "false",
            }

            if info.is_noise:
                noise_count += 1

            doc = Document(text=text, metadata=metadata)
            documents.append(doc)

        pdf.close()
        print(f"✓ 已加载 {len(documents)} 页（跳过 {skipped} 个空白页，{noise_count} 个噪声页）")

        return documents

    # ── 索引构建 ──────────────────────────────────────────────

    def build_index(self, documents: List[Document], exclude_noise: bool = True) -> None:
        """从文档列表构建向量索引

        使用 ChromaDB 原生 API 直接写入（绕过 LlamaIndex 的 from_documents），
        确保 metadata 和数据一致性。

        Args:
            documents: LlamaIndex Document 列表
            exclude_noise: 是否排除噪声页（导言/目录/附录等）
        """
        if exclude_noise:
            original_count = len(documents)
            documents = [d for d in documents if d.metadata.get("is_noise") != "true"]
            excluded = original_count - len(documents)
            if excluded > 0:
                print(f"  过滤掉 {excluded} 个噪声页")

        print(f"🔨 构建向量索引（{len(documents)} 页）...")

        # 删除旧集合（如果存在）
        try:
            self.chroma_client.delete_collection(self.config.collection_name)
        except Exception:
            pass

        collection = self.chroma_client.create_collection(self.config.collection_name)

        # 分块文本
        node_parser = SentenceSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )

        # 将 Document 转为节点并分块
        all_chunks = []
        for doc in documents:
            nodes = node_parser.get_nodes_from_documents([doc])
            for node in nodes:
                node.metadata.update(doc.metadata)
                all_chunks.append(node)

        print(f"  分块完成: {len(all_chunks)} 个文本块")

        # 批量生成嵌入并写入
        from openai import OpenAI
        client = OpenAI(api_key=self.config.api_key, base_url=self.config.api_base)

        batch_size = 32
        total = len(all_chunks)
        for i in range(0, total, batch_size):
            batch = all_chunks[i:i + batch_size]
            texts = [n.text for n in batch]
            response = client.embeddings.create(
                model=self.config.embedding_model,
                input=texts,
            )
            embeddings = [item.embedding for item in response.data]
            ids = [f"chunk_{j}" for j in range(i, i + len(batch))]
            docs = [n.text for n in batch]
            metadatas = []
            for n in batch:
                meta = {}
                for k, v in n.metadata.items():
                    if isinstance(v, str):
                        meta[k] = v
                    else:
                        meta[k] = str(v)
                metadatas.append(meta)

            collection.add(ids=ids, documents=docs, embeddings=embeddings, metadatas=metadatas)

            if (i // batch_size) % 10 == 0:
                print(f"  嵌入进度: {min(i + batch_size, total)}/{total}")

        print(f"✓ 索引构建完成: {collection.count()} 条向量")

        # 同时创建 LlamaIndex 索引用于 retrieve
        chroma_collection = self.chroma_client.get_collection(self.config.collection_name)
        self.vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        self.index = VectorStoreIndex.from_vector_store(self.vector_store)

    def load_index(self) -> None:
        """从已有的 ChromaDB 加载索引（不重新构建）"""
        chroma_collection = self.chroma_client.get_or_create_collection(
            name=self.config.collection_name
        )
        self.vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        self.index = VectorStoreIndex.from_vector_store(self.vector_store)
        print(f"✓ 已加载索引: {self.config.collection_name}")

    def ingest(self, pdf_path: Optional[str] = None) -> None:
        """一键加载 PDF 并构建索引

        Args:
            pdf_path: PDF 文件路径。如果为 None，使用 config.pdf_path。
        """
        documents = self.load_pdf(pdf_path)
        self.build_index(documents)

    # ── 搜索 ──────────────────────────────────────────────────

    def search(self, query: str, top_k: Optional[int] = None,
               chapter: Optional[str] = None, exclude_noise: bool = True) -> str:
        """执行语义搜索，返回综合回答

        Args:
            query: 查询文本
            top_k: 返回结果数量（覆盖 config.top_k）
            chapter: 过滤条件，只搜索该章节的内容
            exclude_noise: 是否排除噪声页

        Returns:
            搜索结果字符串
        """
        if not self.index:
            raise ValueError("索引未初始化，请先调用 ingest() 或 load_index()")

        k = top_k or self.config.top_k
        # LlamaIndex query engine 不直接支持 metadata 过滤
        # 所以用 retrieve + 过滤 再构造回答
        nodes = self.retrieve(query, top_k=k, chapter=chapter, exclude_noise=exclude_noise)
        if not nodes:
            return "未找到相关内容"

        # 拼接为综合回答
        parts = []
        for node in nodes:
            ch = node.metadata.get("chapter", "")
            sec = node.metadata.get("section", "")
            page = node.metadata.get("page", "?")
            label = sec if sec else ch
            prefix = f"[{label} · 页{page}] " if label else f"[页{page}] "
            parts.append(prefix + node.text.strip())
        return "\n\n".join(parts)

    def list_chapters(self, pdf_path: Optional[str] = None) -> List[Dict]:
        """列出 PDF 中检测到的所有章节（树形结构）"""
        path = self._resolve_pdf_path(pdf_path)
        _, chapters = analyze_pdf_structure(path)
        return chapters

    def retrieve(self, query: str, top_k: Optional[int] = None,
                 chapter: Optional[str] = None, exclude_noise: bool = True) -> list:
        """执行相似度检索，返回原始节点列表（含分数和页码）

        Args:
            query: 查询文本
            top_k: 返回结果数量
            chapter: 过滤条件，只返回属于该章节的结果（模糊匹配）
            exclude_noise: 是否排除噪声页

        Returns:
            NodeWithScore 列表
        """
        if not self.index:
            raise ValueError("索引未初始化，请先调用 ingest() 或 load_index()")

        k = top_k or self.config.top_k
        # 如果有过滤条件，多取一些再过滤
        fetch_k = k * 5 if (chapter or exclude_noise) else k
        retriever = self.index.as_retriever(similarity_top_k=fetch_k)
        nodes = retriever.retrieve(query)

        # metadata 过滤
        filtered = []
        for node in nodes:
            if _passes_filter(node.metadata, chapter, exclude_noise):
                filtered.append(node)
                if len(filtered) >= k:
                    break

        return filtered

    # ── 集合管理 ──────────────────────────────────────────────

    def add_pdf(self, pdf_path: str) -> None:
        """向已有索引添加新 PDF"""
        documents = self.load_pdf(pdf_path)
        if not self.index:
            self.load_index()
        for doc in documents:
            self.index.insert(documents=[doc])
        print(f"✓ 已添加 {pdf_path}")

    def list_collections(self) -> list:
        """列出所有集合"""
        return [c.name for c in self.chroma_client.list_collections()]

    def delete_collection(self, name: Optional[str] = None) -> None:
        """删除指定集合"""
        target = name or self.config.collection_name
        self.chroma_client.delete_collection(target)
        print(f"✓ 已删除集合: {target}")

    def collection_info(self, name: Optional[str] = None) -> Dict[str, Any]:
        """获取集合信息"""
        target = name or self.config.collection_name
        try:
            coll = self.chroma_client.get_collection(target)
            return {"name": target, "count": coll.count()}
        except Exception:
            return {"name": target, "count": 0, "error": "集合不存在"}


# ── 直接 ChromaDB 查询（绕过 LlamaIndex）──────────────────

def _passes_filter(meta: dict, chapter: Optional[str] = None,
                    exclude_noise: bool = True,
                    exclude_chapters: Optional[List[str]] = None) -> bool:
    """检查 metadata 是否通过过滤条件（retrieve 和 direct_query 共享）"""
    if exclude_noise and meta.get("is_noise") == "true":
        return False
    if chapter:
        # 在 chapter/section/subsection 中模糊匹配
        ch = meta.get("chapter", "")
        sec = meta.get("section", "")
        sub = meta.get("subsection", "")
        if chapter not in ch and chapter not in sec and chapter not in sub:
            return False
    if exclude_chapters:
        ch = meta.get("chapter", "") + meta.get("section", "") + meta.get("subsection", "")
        if any(ex in ch for ex in exclude_chapters):
            return False
    return True


def direct_query(config, query: str, n_results: int = 3,
                 chapter: Optional[str] = None, exclude_noise: bool = True,
                 exclude_chapters: Optional[List[str]] = None) -> list:
    """直接使用 ChromaDB + OpenAI Embedding 查询（不经过 LlamaIndex）

    Args:
        config: Config 对象
        query: 查询文本
        n_results: 返回结果数量
        chapter: 只返回属于该章节的结果（模糊匹配）
        exclude_noise: 是否排除噪声页
        exclude_chapters: 排除指定章节列表（模糊匹配）

    Returns:
        结果列表，每项包含 text, page, distance, chapter, section
    """
    from openai import OpenAI

    client = OpenAI(api_key=config.api_key, base_url=config.api_base)
    response = client.embeddings.create(
        model=config.embedding_model,
        input=[query],
    )
    embedding = response.data[0].embedding

    chroma_client = chromadb.PersistentClient(path=config.db_path)
    collection = chroma_client.get_collection(config.collection_name)

    # 多取一些再过滤
    fetch_k = n_results * 5 if (chapter or exclude_noise or exclude_chapters) else n_results
    results = collection.query(
        query_embeddings=[embedding],
        n_results=fetch_k,
        include=["documents", "metadatas", "distances"],
    )

    items = []
    for i in range(len(results["documents"][0])):
        meta = results["metadatas"][0][i]
        if not _passes_filter(meta, chapter, exclude_noise, exclude_chapters):
            continue
        items.append({
            "text": results["documents"][0][i],
            "page": meta.get("page", "?"),
            "distance": results["distances"][0][i],
            "chapter": meta.get("chapter", ""),
            "section": meta.get("section", ""),
        })
        if len(items) >= n_results:
            break
    return items
