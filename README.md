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

# 2. 配置 API Key（创建 config.py）
os.environ["DASHSCOPE_API_KEY"] = "your-key"

# 3. 启动
streamlit run app.py
```

## 📁 项目结构

```
├── app.py                 # 前端界面
├── backend/
│   ├── agent.py          # RAG Agent
│   └── document_manager.py # 文档管理
└── data/                 # 数据存储
```

## 🔧 核心依赖

- `streamlit` - 前端界面
- `langgraph` - Agent 工作流
- `langchain-chroma` - 向量数据库
- `dashscope` - 通义千问模型