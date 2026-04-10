import os,shutil,hashlib,json
from langchain_community.document_loaders import (
    TextLoader,           # .txt
    UnstructuredWordDocumentLoader,  # .doc/.docx
    CSVLoader,            # .csv
    UnstructuredMarkdownLoader,  # .md
    PyPDFLoader,          # .pdf
) 
from langchain_chroma import Chroma
from datetime import datetime
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pathlib import Path
from config import DATA_PATH
# 文件格式映射
SUPPORTED_EXTENSIONS = {
    '.pdf': PyPDFLoader,
    '.txt': TextLoader,
    '.docx': UnstructuredWordDocumentLoader,
    '.csv': CSVLoader,
    '.md': UnstructuredMarkdownLoader,
}


# 新增文档管理模块
class DocumentManager:
    def __init__(self, embeddings: DashScopeEmbeddings =None):
        self.data_path = DATA_PATH/ "data"
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.db_path = str(self.data_path / "chroma_db")
        self.embeddings = embeddings # 注入embedding模型
        self.vectordb = self._get_db() # 初始化向量库

        self.METADATA_FILE = str(self.data_path / "documents_metadata.json")  # 存储文档元数据的文件
        self.upload_dir = str(self.data_path / "uploaded_files")  # 保存原始文件的目录

        self.metadata = {} # 文档元数据
        self.fingerprints = set()  # 已加载文档的指纹集合
        self.document_names = set()  # 已加载文档的名称集合
        
        self._load_metadata()  # 加载文档元数据
        self._update_fp_dn()   # 更新指纹和名称集合

    def _load_metadata(self)->str:
        """加载文档元数据"""
        if os.path.exists(self.METADATA_FILE):
            with open(self.METADATA_FILE, 'r', encoding='utf-8') as f:
                self.metadata =  json.load(f)
                return "✅ 成功加载文档元数据"
        return "❌ 没有找到文档元数据文件，已初始化空数据"
    
    def _update_fp_dn(self):
        """更新指纹和名称集合"""
        self.fingerprints = set(doc_info["fingerprint"] for doc_info in self.metadata.values())
        self.document_names = set(key for key in self.metadata.keys())

    def _update(self):
        """保存文档元数据并更新集合"""
        with open(self.METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        self._update_fp_dn()

    def _get_document_fingerprint(self, file_path: str) -> str:
        """计算文档的哈希值作为唯一标识"""
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
   
    def _upload_document(self, file_path):
        """加载文档内容"""
        ext = os.path.splitext(file_path)[1].lower()
        loader_class = SUPPORTED_EXTENSIONS.get(ext)
        if not loader_class:
            raise ValueError(f"不支持的文件格式: {ext}")
        loader = loader_class(file_path)
        return loader.load()

    def _split_text(self, documents):
        """切分文本为块"""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=20,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
        )
        chunks = splitter.split_documents(documents)
        return chunks

    def _get_db(self):
        """获取向量库实例（如果存在则读取，不存在则创建空库）"""
        # 确保目录存在
        os.makedirs(self.db_path, exist_ok=True)
        
        # 获取向量库实例（不自动创建collection，只是连接）
        vectordb = Chroma(
            persist_directory=self.db_path,
            embedding_function=self.embeddings,
        )
        
        # 检查是否有内容
        count = vectordb._collection.count()
        if count == 0:
            print("向量库已创建（当前为空）")
        else:
            print(f"✅ 成功读取向量库，包含 {count} 个文本块")
        
        return vectordb
        
    def _add_db(self, chunks, fingerprint=None, doc_id=None):
        """添加文档块到向量库，并记录 fingerprint"""
        if not chunks:
            print("没有要添加的文档块")
            return 
        
        # 为每个 chunk 添加 fingerprint 和 doc_id 到 metadata
        for i, chunk in enumerate(chunks):
            if fingerprint:
                chunk.metadata["fingerprint"] = fingerprint
            if doc_id:
                chunk.metadata["doc_id"] = doc_id
            chunk.metadata["chunk_index"] = i
        
        # 添加文档块
        if self.vectordb._collection.count() > 0:
            self.vectordb.add_documents(chunks)
            print(f"✅ 增量添加 {len(chunks)} 个块")
        else:
            self.vectordb.add_documents(chunks)
            print(f"✅ 首次添加 {len(chunks)} 个块")
        
        return 
    
    def add_document(self, file_path: str, doc_id: str)-> str:
        """添加文档"""

        # 1. 计算文档指纹，检查是否已加载过
        fingerprint = self._get_document_fingerprint(file_path)

        if fingerprint in self.fingerprints:
            return "文档已经加载过了，无需重复加载！"
        
        if doc_id in self.document_names:
            return "文档名称已存在，请更换名称后再试！"
        
        # 2. 确保上传目录存在，复制文件到上传目录，并保存元数据
        os.makedirs(self.upload_dir, exist_ok=True)

        original_ext = os.path.splitext(file_path)[1]
        saved_path = os.path.join(self.upload_dir, f"{doc_id}{original_ext}")
        shutil.copy2(file_path, saved_path)

        self.metadata[doc_id] = {
            "saved_path": saved_path,  
            "fingerprint": fingerprint,
            "created_at": datetime.now().isoformat()
        }

        # 3. 切分文本并添加到向量库
        chunks = self._split_text(self._upload_document(file_path))
        self._add_db(chunks=chunks, fingerprint=fingerprint, doc_id=doc_id)

        # 4. 更新指纹和名称集合，并保存元数据
        self._update()

        return "文档加载成功！"
        
    def _delete_from_vector_db(self, fingerprint: str):
        """从向量库删除文档的所有块"""
        try:
            # 删除所有 fingerprint 匹配的块
            self.vectordb._collection.delete(
                where={"fingerprint": fingerprint}
            )
            print(f"✅ 已从向量库删除文档")
                
        except Exception as e:
            print(f"删除向量库内容失败: {e}")

    def delete_document(self, doc_id: str):
        """删除文档（删除原始文件 + 元数据 + 向量库内容）"""
        try:
            # 1. 检查文档是否存在
            if doc_id not in self.metadata:
                return {"status": "error", "message": "文档不存在"}
            
            doc_info = self.metadata[doc_id]
            
            # 2. 删除原始文件
            if os.path.exists(doc_info["saved_path"]):
                os.remove(doc_info["saved_path"])
                print(f"✅ 已删除文件: {doc_info['saved_path']}")
            
            # 3. 删除向量库中的内容（通过 fingerprint 或 doc_id 过滤）
            self._delete_from_vector_db(doc_info["fingerprint"])
         
            # 4. 删除元数据
            del self.metadata[doc_id]
            
            # 5. 持久化数据并更新集合
            self._update()
            
            return {
                "status": "success",
                "message": f"文档删除成功: {doc_id}" 
            }           
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
        
    def list_documents(self)-> set:
        """列出所有文档"""
        return self.document_names
