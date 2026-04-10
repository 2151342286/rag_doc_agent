# RAG 智能助手

基于 LangGraph + Streamlit 的文档智能问答系统。

## ✨ 功能

- 📄 支持 PDF、TXT、DOCX、CSV、MD 格式
- 🔍 语义检索 + 对话式问答
- 📁 文档上传/下载/删除管理
- 🎯 严格基于文档内容回答

## 🚀 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境（创建。env文件）
。env文件内容：
LLM_MODEL_ID="xxx"
LLM_API_KEY= "xxx"
LLM_BASE_URL="xxx"
EMBEDDING_MODEL_ID="xxx"

# 3. 启动
streamlit run app.py
```

## 📁 项目结构

```
├── __pycache__/
├── app.py                 # 前端界面
├── backend/
│   ├── agent.py          # RAG Agent
│   └── document_manager.py # 文件管理类
└── data/                 # 数据存储
│   ├── chroma_db/         # 向量库
│   └── uploaded_files/ # 上传的文件
|   └──documents_metadata.json # 文件元数据（简要信息）
└── config.py  # 配置文件
| 
└── 。env  # 环境变量 
```

## 🔧 核心依赖

- `streamlit` - 前端界面
- `langgraph` - Agent 工作流
- `langchain-chroma` - 向量数据库
- `dashscope` - 通义千问模型
