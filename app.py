# app.py
import streamlit as st
from backend.agent import RAGAgent
from backend.document_manager import DocumentManager
from config import embeddings
import tempfile
import os
import base64

class StreamlitApp:
    """Streamlit 前端应用"""
    
    def __init__(self):
        self._init_session_state()
    
    def _init_session_state(self):
        """初始化 session state 变量"""
        if "doc_manager" not in st.session_state:
            st.session_state.doc_manager = DocumentManager(embeddings=embeddings)

        if "agent" not in st.session_state:
            st.session_state.agent = RAGAgent(doc_manager=st.session_state.doc_manager)
        
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        # 输入框清空用的key
        if "input_key" not in st.session_state:
            st.session_state.input_key = 0
    
    def render_sidebar(self):
        """渲染左侧边栏"""
        with st.sidebar:
            st.title("📁 文档管理")
            st.divider()
            
            st.subheader("📤 上传文档")
            uploaded_file = st.file_uploader(
                "选择文件",
                type=['pdf', 'txt', 'docx', 'csv', 'md'],
                help="支持 PDF、TXT、DOCX、CSV、MD 格式"
            )
            
            if uploaded_file is not None:
                doc_name = os.path.splitext(uploaded_file.name)[0]
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    doc_name_input = st.text_input(
                        "文档名称",
                        value=doc_name,
                        key="doc_name_input",
                        label_visibility="collapsed"
                    )
                with col2:
                    if st.button("📥 上传", type="primary", use_container_width=True):
                        if doc_name_input.strip():
                            self._upload_document(uploaded_file, doc_name_input.strip())
                        else:
                            st.error("请输入文档名称")
            
            st.divider()
            st.subheader("📚 已加载文档")
            self._render_document_list()
    
    def _upload_document(self, uploaded_file, doc_name: str):
        """上传文档到系统"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{uploaded_file.name}") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            
            result = st.session_state.doc_manager.add_document(tmp_path, doc_name)
            os.unlink(tmp_path)
            
            if "成功" in result or "✅" in result:
                st.success(f"✅ 文档 '{doc_name}' 上传成功！")
                st.session_state.agent.doc_manager = st.session_state.doc_manager
                st.rerun()
            else:
                st.warning(result)
        except Exception as e:
            st.error(f"上传失败：{str(e)}")
    
    def _render_document_list(self):
        """渲染文档列表"""
        documents = st.session_state.doc_manager.list_documents()
        
        if not documents:
            st.info("暂无文档，请上传")
            return
        
        for doc_id in documents:
            doc_info = st.session_state.doc_manager.metadata.get(doc_id, {})
            file_path = doc_info.get("saved_path", "")
            
            col1, col2, col3 = st.columns([4, 1, 1])
            
            with col1:
                st.markdown(f"📄 **{doc_id}**")
                
                created_at = doc_info.get('created_at', '未知时间')
                if 'T' in created_at:
                    created_at = created_at.replace('T', ' ')[:19]
                st.caption(f"📅 {created_at}")
                
                if file_path and os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    if file_size < 1024:
                        size_str = f"{file_size} B"
                    elif file_size < 1024 * 1024:
                        size_str = f"{file_size / 1024:.1f} KB"
                    else:
                        size_str = f"{file_size / (1024 * 1024):.1f} MB"
                    st.caption(f"📦 {size_str}")
                else:
                    st.caption("⚠️ 仅向量索引")
            
            with col2:
                if file_path and os.path.exists(file_path):
                    download_link = self._get_download_link(file_path, f"{doc_id}{os.path.splitext(file_path)[1]}")
                    st.markdown(download_link, unsafe_allow_html=True)
                else:
                    st.button("📥", disabled=True, key=f"download_disabled_{doc_id}")
            
            with col3:
                if st.button("🗑️", key=f"del_{doc_id}", use_container_width=True):
                    self._delete_document(doc_id)
                    st.rerun()
            st.divider()
    
    def _get_download_link(self, file_path: str, file_name: str) -> str:
        """生成文件下载链接"""
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            b64 = base64.b64encode(data).decode()
            return f'<a href="data:application/octet-stream;base64,{b64}" download="{file_name}">📥 下载</a>'
        except:
            return "⚠️ 失败"
    
    def _delete_document(self, doc_id: str):
        """删除文档"""
        result = st.session_state.doc_manager.delete_document(doc_id)
        if result.get("status") == "success":
            st.success(f"✅ 已删除 '{doc_id}'")
            st.session_state.agent.doc_manager = st.session_state.doc_manager
        else:
            st.error(f"删除失败：{result.get('message', '未知错误')}")
    
    def render_chat_interface(self):
        """渲染右侧对话界面"""
        st.title("🤖 RAG 智能助手")
        st.caption("基于文档的智能问答系统")
        
        # 聊天历史容器
        chat_container = st.container()
        
        with chat_container:
            self._render_chat_history()
        
        # 输入区域放在下面
        self._render_input_area()
    
    def _render_chat_history(self):
        """渲染对话历史 - 微信风格左右气泡"""
        messages = st.session_state.messages
        
        if not messages:
            st.info("💡 开始对话吧！上传文档后，我可以帮你回答问题。")
            return
        
        # 微信风格CSS
        st.markdown("""
            <style>
            .chat-container {
                display: flex;
                flex-direction: column;
                gap: 12px;
                padding: 10px 0;
            }
            .message-row {
                display: flex;
                width: 100%;
                margin-bottom: 16px;
            }
            .message-row.user {
                justify-content: flex-end;
            }
            .message-row.assistant {
                justify-content: flex-start;
            }
            .message-bubble {
                max-width: 70%;
                padding: 10px 14px;
                border-radius: 18px;
                word-wrap: break-word;
                line-height: 1.4;
            }
            .message-bubble.user {
                background-color: #95ec69;
                color: #000;
                border-bottom-right-radius: 4px;
            }
            .message-bubble.assistant {
                background-color: #ffffff;
                color: #000;
                border: 1px solid #e9ecef;
                border-bottom-left-radius: 4px;
            }
            .message-time {
                font-size: 10px;
                color: #999;
                margin-top: 4px;
                text-align: center;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # 渲染消息
        for idx, msg in enumerate(messages):
            role = msg["role"]
            content = msg["content"]
            
            if role == "user":
                st.markdown(f"""
                    <div class="message-row user">
                        <div class="message-bubble user">{content}</div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class="message-row assistant">
                        <div class="message-bubble assistant">{content}</div>
                    </div>
                """, unsafe_allow_html=True)
    
    def _render_input_area(self):
        """渲染输入区域"""
        st.markdown("---")
        
        # 输入行
        col1, col2 = st.columns([5, 1])
        
        with col1:
            user_input = st.text_input(
                "输入您的问题",
                placeholder="输入您的问题...",
                key=f"user_input_{st.session_state.input_key}",
                label_visibility="collapsed"
            )
        
        with col2:
            send_button = st.button(
                "发送 ✨",
                type="primary",
                use_container_width=True
            )
        
        # 按钮行
        col3, col4 = st.columns(2)
        with col3:
            if st.button("🗑️ 清空对话", use_container_width=True):
                self._clear_chat_history()
                st.rerun()
        with col4:
            if st.button("🔄 重置Agent", use_container_width=True):
                self._reset_agent()
                st.rerun()
        
        # 处理发送
        if send_button and user_input:
            self._handle_user_input(user_input)
    
    def _handle_user_input(self, user_input: str):
        """处理用户输入"""
        # 1. 添加用户消息
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })
        
        # 2. 清空输入框
        st.session_state.input_key += 1
        
        # 3. 获取AI回复
        try:
            response = st.session_state.agent.run(user_input)
            st.session_state.messages.append({
                "role": "assistant",
                "content": response
            })
        except Exception as e:
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"❌ 处理失败：{str(e)}"
            })
        
        # 4. 刷新页面
        st.rerun()
    
    def _clear_chat_history(self):
        """清空对话历史"""
        st.session_state.messages = []
        st.session_state.agent.reset_conversation()
        st.success("✅ 对话历史已清空")
    
    def _reset_agent(self):
        """重置 Agent"""
        st.session_state.agent = RAGAgent(doc_manager=st.session_state.doc_manager)
        st.session_state.messages = []
        st.success("✅ Agent 已重置")
    
    def run(self):
        """运行应用"""
        st.set_page_config(
            page_title="RAG 智能助手",
            page_icon="🤖",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # CSS 去除空白
        st.markdown("""
            <style>
            .main .block-container {
                max-width: 100% !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # 两列布局
        col_left, col_right = st.columns([1, 2.5], gap="medium")
        
        with col_left:
            self.render_sidebar()
        
        with col_right:
            self.render_chat_interface()


if __name__ == "__main__":
    app = StreamlitApp()
    app.run()