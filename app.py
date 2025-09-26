from typing import Callable, TypeVar
import os
import inspect
import streamlit as st
import streamlit_analytics2 as streamlit_analytics
from dotenv import load_dotenv
from streamlit_chat import message
from streamlit_pills import pills
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
from streamlit.delta_generator import DeltaGenerator
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from custom_callback_handler import CustomStreamlitCallbackHandler
from agents import define_graph
import shutil
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

# 从Streamlit secrets或.env设置环境变量
os.environ["LINKEDIN_EMAIL"] = st.secrets.get("LINKEDIN_EMAIL", "")
os.environ["LINKEDIN_PASS"] = st.secrets.get("LINKEDIN_PASS", "")
os.environ["LANGCHAIN_API_KEY"] = st.secrets.get("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2") or st.secrets.get("LANGCHAIN_TRACING_V2", "")
os.environ["LANGCHAIN_PROJECT"] = st.secrets.get("LANGCHAIN_PROJECT", "")
os.environ["SERPER_API_KEY"] = st.secrets.get("SERPER_API_KEY", "")
os.environ["FIRECRAWL_API_KEY"] = st.secrets.get("FIRECRAWL_API_KEY", "")
os.environ["LINKEDIN_SEARCH"] = st.secrets.get("LINKEDIN_JOB_SEARCH", "")
os.environ["DASHSCOPE_API_KEY"] = st.secrets.get("DASHSCOPE_API_KEY", "")

# 页面配置
st.set_page_config(layout="wide")
st.title("JobPilot 职业助手 - 👨‍💼")
st.markdown("[联系作者 QQ 邮箱](http://mail.qq.com/cgi-bin/qm_share?t=qm_mailme&email=V2RmYmRjZm9mbmIXJiZ5NDg6)")

streamlit_analytics.start_tracking()

# 🔴 优化：简化目录和路径设置
temp_dir = "temp"
dummy_resume_path = os.path.abspath("dummy_resume.pdf")

if not os.path.exists(temp_dir):
    os.makedirs(temp_dir)


uploaded_document = st.sidebar.file_uploader("上传你的简历（PDF）", type="pdf")

# 🔴 优化：简化简历处理逻辑
if not uploaded_document:
    # 检查是否有演示简历
    if os.path.exists(dummy_resume_path):
        uploaded_document = open(dummy_resume_path, "rb")
        st.sidebar.write("未上传简历，正在使用演示简历。")
        st.sidebar.markdown(f"[查看演示简历]({'https://drive.google.com/file/d/1vTdtIPXEjqGyVgUgCO6HLiG9TSPcJ5eM/view?usp=sharing'})")
    else:
        st.sidebar.write("📝 请上传您的简历以开始使用职业助手功能")
        uploaded_document = None
        
# 🔴 优化：避免重复保存简历
if uploaded_document:
    # 检查是否是新文件
    current_filename = getattr(uploaded_document, 'name', 'dummy_resume.pdf')
    if not st.session_state.get("resume_saved", False) or st.session_state.get("resume_filename", "") != current_filename:
        bytes_data = uploaded_document.read()
        filepath = os.path.join(temp_dir, "resume.pdf")
        with open(filepath, "wb") as f:
            f.write(bytes_data)
        
        # 更新会话状态
        st.session_state["resume_saved"] = True
        st.session_state["resume_filename"] = current_filename
        
        print(f"新简历已保存: {current_filename}, 简历已保存到: {filepath}, 大小: {len(bytes_data)} bytes")
        st.sidebar.markdown("**✅ 简历上传成功！**")
    else:
        st.sidebar.markdown(f"**✅ 已加载简历：{current_filename}**")

# 通义千问配置
if st.secrets.get("DASHSCOPE_API_KEY", ""):
    st.sidebar.markdown("✅ 已从配置中加载 DashScope API 密钥")
    api_key_tongyi = st.secrets.get("DASHSCOPE_API_KEY", "")
else:
    api_key_tongyi = st.sidebar.text_input(
        "DashScope（通义千问）API 密钥",
        st.session_state.get("DASHSCOPE_API_KEY", ""),
        type="password",
    )

model_tongyi = st.sidebar.selectbox(
    "选择通义千问模型",
    ("qwen-turbo", "qwen-plus", "qwen-max", "qwen-max-1201"),
    help="推荐使用 qwen-plus 或 qwen-max 以获得更好的工具调用支持"
)

settings = {
    "model": model_tongyi,
    "model_provider": "tongyi",
    "temperature": 0.3,
    "DASHSCOPE_API_KEY": api_key_tongyi,
}
st.session_state["DASHSCOPE_API_KEY"] = api_key_tongyi
os.environ["DASHSCOPE_API_KEY"] = api_key_tongyi

# 🔴 优化：添加功能状态显示，参考app copy.py的侧边栏信息
st.sidebar.markdown("### 🛠️ 功能状态")
if st.secrets.get("SERPER_API_KEY", ""):
    st.sidebar.markdown("✅ SerpAPI 搜索功能已启用")
else:
    st.sidebar.markdown("⚠️ SerpAPI 未配置，搜索功能受限")

if st.secrets.get("FIRECRAWL_API_KEY", ""):
    st.sidebar.markdown("✅ FireCrawl 网页抓取已启用")
else:
    st.sidebar.markdown("⚠️ FireCrawl 未配置，网页抓取受限")

if model_tongyi in ["qwen-plus", "qwen-max", "qwen-max-1201"]:
    st.sidebar.markdown("✅ 支持高级工具调用功能")
else:
    st.sidebar.markdown("⚠️ 基础模型，部分高级功能可能受限")

# 创建代理流程
flow_graph = define_graph()
message_history = StreamlitChatMessageHistory()

# 初始化会话状态变量
if "active_option_index" not in st.session_state:
    st.session_state["active_option_index"] = None
if "interaction_history" not in st.session_state:
    st.session_state["interaction_history"] = []
if "response_history" not in st.session_state:
    st.session_state["response_history"] = ["你好！请问你需要什么帮助?"]
if "user_query_history" not in st.session_state:
    st.session_state["user_query_history"] = ["你好! 👋"]
if "resume_saved" not in st.session_state:
    st.session_state["resume_saved"] = False
if "resume_filename" not in st.session_state:
    st.session_state["resume_filename"] = ""
if "DASHSCOPE_API_KEY" not in st.session_state:
    st.session_state["DASHSCOPE_API_KEY"] = ""

# 聊聊界面的容器
conversation_container = st.container()
input_section = st.container()

def initialize_callback_handler(main_container: DeltaGenerator):
    V = TypeVar("V")

    def wrap_function(func: Callable[..., V]) -> Callable[..., V]:
        context = get_script_run_ctx()

        def wrapped(*args, **kwargs) -> V:
            add_script_run_ctx(ctx=context)
            return func(*args, **kwargs)

        return wrapped

    streamlit_callback_instance = CustomStreamlitCallbackHandler(
        parent_container=main_container
    )

    for method_name, method in inspect.getmembers(
        streamlit_callback_instance, predicate=inspect.ismethod
    ):
        setattr(streamlit_callback_instance, method_name, wrap_function(method))

    return streamlit_callback_instance

# 🔴 优化：简化对话执行逻辑
def execute_chat_conversation(user_input, graph):
    callback_handler_instance = initialize_callback_handler(st.container())
    callback_handler = callback_handler_instance
    try:
        print(f"执行对话，用户输入: {user_input}")
        
        # 清除之前的agent序列
        callback_handler.clear_agent_sequence()
        
        # 🔴 优化：简化消息处理
        output = graph.invoke(
            {
                "messages": list(message_history.messages) + [HumanMessage(content=user_input)],
                "user_input": user_input,
                "config": settings,
                "callback": callback_handler,
                "recursion_count": 0,  # 初始化递归计数
            },
            {"recursion_limit": 15},  # 增加递归限制以支持多步骤任务
        )
        
        # 显示agent执行序列
        agent_sequence = callback_handler.get_agent_sequence()
        if agent_sequence:
            st.markdown("**🤖 Agent执行顺序:**")
            agent_emojis = []
            for agent in agent_sequence:
                if "ResumeAnalyzer" in agent:
                    agent_emojis.append("📄")
                elif "JobSearcher" in agent:
                    agent_emojis.append("💼")
                elif "CoverLetterGenerator" in agent:
                    agent_emojis.append("✍️")
                elif "WebResearcher" in agent:
                    agent_emojis.append("🔍")
                elif "ChatBot" in agent:
                    agent_emojis.append("🤖")
                else:
                    agent_emojis.append("🔄")
            
            st.markdown(" → ".join([f"{emoji} {agent}" for emoji, agent in zip(agent_emojis, agent_sequence)]))
        
        # 🔴 优化：简化消息提取
        message_output = output.get("messages")[-1]
        messages_list = output.get("messages")
        message_history.clear()
        message_history.add_messages(messages_list)
        
        return message_output.content

    except Exception as exc:
        print(f"详细错误: {exc}")
        import traceback
        traceback.print_exc()
        st.error(f"执行错误: {str(exc)}")
        return ":( Sorry, Some error occurred. Can you please try again?"

# 清除聊天功能
if st.button("清除聊天"):
    st.session_state["user_query_history"] = []
    st.session_state["response_history"] = []
    message_history.clear()
    st.rerun()

streamlit_analytics.start_tracking()

# 显示聊天界面
with input_section:
    options = [
        "识别与GenAI相关的科技行业最新趋势",
        "查找新兴技术及其对岗位机会的影响",
        "总结我的简历",
        "根据我的简历技能和兴趣生成职业路径可视化",
        "阿里的GenAI相关岗位",
        "在中国搜索GenAI相关岗位",
        "分析我的简历并推荐合适岗位及相关职位列表",
        "为我的简历生成求职信",
    ]
    icons = ["🔍", "🌐", "📝", "📈", "💼", "🌟", "✉️", "🧠"]

    selected_query = pills(
        "请选择一个问题进行查询：",
        options,
        clearable=None,
        icons=icons,
        index=st.session_state["active_option_index"],
        key="pills",
    )
    if selected_query:
        st.session_state["active_option_index"] = options.index(selected_query)

    # 显示文本输入表单
    with st.form(key="query_form", clear_on_submit=True):
        user_input_query = st.text_input(
            "请输入你的问题：",
            value=(selected_query if selected_query else ""),
            placeholder="📝 请输入您的问题，或从上方选择一个预设选项开始对话",
            key="input",
        )
        submit_query_button = st.form_submit_button(label="发送")

    if submit_query_button:
        # 🔴 优化：简化验证逻辑
        if not uploaded_document:
            st.error("请先上传您的简历，然后再提交查询。")
        elif not api_key_tongyi and not st.secrets.get("DASHSCOPE_API_KEY", ""):
            st.error("请先输入 DashScope API 密钥。")
        elif user_input_query:
            # 🔴 优化：简化查询处理
            chat_output = execute_chat_conversation(user_input_query, flow_graph)
            st.session_state["user_query_history"].append(user_input_query)
            st.session_state["response_history"].append(chat_output)
            st.session_state["last_input"] = user_input_query
            st.session_state["active_option_index"] = None

# 显示聊天历史
if st.session_state["response_history"]:
    with conversation_container:
        for i in range(len(st.session_state["response_history"])):
            message(
                st.session_state["user_query_history"][i],
                is_user=True,
                key=str(i) + "_user",
                avatar_style="fun-emoji",
            )
            message(
                st.session_state["response_history"][i],
                key=str(i),
                avatar_style="bottts",
            )

streamlit_analytics.stop_tracking()