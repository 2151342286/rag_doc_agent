# rag_agent.py
from typing import List, Dict
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.prebuilt import ToolNode
from config import model
from backend.document_manager import DocumentManager


class RAGAgent:
    def __init__(self,doc_manager: DocumentManager):
        # 初始化文档管理器
        self.doc_manager = doc_manager
        
        # 定义工具
        self.tools = self._create_tools()
        
        # 绑定工具到 LLM
        self.llm_with_tools = model.bind_tools(self.tools)
        
        # 构建 LangGraph 工作流
        self.app = self._build_graph()
        
        # 对话历史存储
        self.chat_history = []
    
    def _create_tools(self):
        """创建 Agent 可用的工具集（使用 @tool 装饰器）"""
        
        @tool
        def search_documents(query: str) -> str:
            """
            在已加载的文档中搜索相关信息。
            当你需要查找特定内容、回答问题或获取文档中的信息时使用。
            
            Args:
                query: 搜索关键词或问题
            """
            try:
                if not self.doc_manager.vectordb:
                    return "错误：尚未加载任何文档，请先使用 upload 命令加载文档"
                
                retriever = self.doc_manager.vectordb.as_retriever(
                    search_kwargs={"k": 4}
                )
                docs = retriever.invoke(query)
                print(f"检索到的文档: {docs}")
                if not docs:
                    return "未找到相关信息"
                
                results = []
                for i, doc in enumerate(docs, 1):
                    source = doc.metadata.get("source", doc.metadata.get("doc_id", "未知文档"))
                    content = doc.page_content[:500]
                    results.append(f"[来源：{source}]\n{content}\n")
                
                return "\n---\n".join(results)
            except Exception as e:
                return f"搜索失败：{str(e)}"
        @tool
        def list_documents() -> str:
            """
            返回当前已加载的文件名称集合
            """
            return self.doc_manager.list_documents()
        
        return [search_documents, list_documents]
    
    def _build_graph(self):
        """构建 LangGraph 工作流"""
        
        # 创建工具节点
        tool_node = ToolNode(self.tools)
        
        # 定义调用模型函数
        def call_model(state: MessagesState):
            messages = state["messages"]
            response = self.llm_with_tools.invoke(messages)
            return {"messages": messages + [response]}
        
        # 定义路由函数：判断是否需要继续调用工具
        def should_continue(state: MessagesState):
            messages = state["messages"]
            last_message = messages[-1]
            
            # 如果 LLM 返回了工具调用请求，则继续执行工具S
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            # 否则结束
            return END
        
        # 构建状态图
        workflow = StateGraph(MessagesState)
        
        # 添加节点
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", tool_node)
        
        # 设置入口
        workflow.set_entry_point("agent")
        
        # 添加条件边
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {
                "tools": "tools",
                END: END
            }
        )
        
        # 工具执行后回到 agent
        workflow.add_edge("tools", "agent")
        
        # 编译
        return workflow.compile()
    
    def run(self, user_input: str) -> str:
        # 构建消息（包含历史对话）
        messages = []
        # 添加 system message 强制约束
        system_prompt = """你是严格的文档问答助手。必须遵守以下规则：

                            1. **只能基于工具返回的内容回答**
                            2. 如果检索到的内容不足以回答问题，明确说"根据现有文档无法回答这个问题"。
                            3. **绝对不要使用你自己的知识**，即使你知道答案
                            4. 回答时要引用来源，格式：[来源：文档名]

                        """
        
        # 检查是否已有 system message
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=system_prompt)] + messages
            # 添加历史对话（最近10轮）
            for hist in self.chat_history[-10:]:
                messages.append(HumanMessage(content=hist["user"]))
                messages.append(AIMessage(content=hist["assistant"]))
            
            # 添加当前问题
            messages.append(HumanMessage(content=user_input))
        
        # 调用 LangGraph
        try:
            final_state = self.app.invoke({"messages": messages})
            final_message = final_state["messages"][-1]
            response = final_message.content
            
            # 保存对话历史
            self.chat_history.append({
                "user": user_input,
                "assistant": response
            })
            
            # 限制历史长度
            if len(self.chat_history) > 20:
                self.chat_history = self.chat_history[-20:]
            
            return response
            
        except Exception as e:
            error_msg = f"Agent 执行失败：{str(e)}"
            print(error_msg)
            return error_msg
    
    def stream_run(self, user_input: str):
        '''后面前端并没有使用'''
        messages = []
        
        for hist in self.chat_history[-10:]:
            messages.append(HumanMessage(content=hist["user"]))
            messages.append(AIMessage(content=hist["assistant"]))
        
        messages.append(HumanMessage(content=user_input))
        
        # 用于收集完整响应的变量
        full_response = ""

        # 流式执行
        for event in self.app.stream({"messages": messages}):
            for node_name, node_output in event.items():
                if "messages" in node_output:
                    message = node_output["messages"][-1]
                    
                    # 判断消息类型
                    if hasattr(message, "tool_calls") and message.tool_calls:
                        # 工具调用
                        yield {
                            "type": "tool_call",
                            "content": f"🔧 调用工具：{message.tool_calls[0]['name']}"
                        }
                    elif message.content:
                        # 普通回答
                        full_response += message.content
                        yield {
                            "type": "response",
                            "content": message.content
                        }
        if full_response:
            self.chat_history.append({
                "user": user_input,
                "assistant": full_response
            })
        
        # 限制历史长度
        if len(self.chat_history) > 20:
            self.chat_history = self.chat_history[-20:]
    
    def reset_conversation(self):
        """重置对话历史"""
        self.chat_history = []
        print("对话历史已清空")
    
    def get_chat_history(self) -> List[Dict]:
        """获取对话历史"""
        return self.chat_history
