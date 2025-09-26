from typing import Any, TypedDict
from langchain.agents import AgentExecutor, create_openai_tools_agent
from llms import get_llm
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import os

from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
from chains import get_finish_chain, get_supervisor_chain
from tools import (
    get_job_search_tool,
    ResumeExtractorTool,
    generate_letter_for_specific_job,
    get_google_search_results, 
    save_cover_letter_for_specific_job,
    scrape_website,
)
from prompts import (
    get_analyzer_agent_prompt_template,
    get_search_agent_prompt_template,
    get_generator_agent_prompt_template,
    researcher_agent_prompt_template,
)

load_dotenv()


def create_agent(llm, tools: list, system_prompt: str):
    """
    Creates an agent using the specified ChatOpenAI model, tools, and system prompt.

    Args:
        llm : LLM to be used to create the agent.
        tools (list): The list of tools to be given to the worker node.
        system_prompt (str): The system prompt to be used in the agent.

    Returns:
        AgentExecutor: The executor for the created agent.
    """
    # Each worker node will be given a name and some tools.
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system",system_prompt,),
            MessagesPlaceholder(variable_name="messages"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )
    agent = create_openai_tools_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools)
    return executor


def init_chat_model(model, model_provider, dashscope_api_key, temperature):
    return get_llm(
        provider=model_provider,
        model=model,
        api_key=dashscope_api_key,
        temperature=temperature,
    )

def supervisor_node(state):
    """
    Supervisor 节点 - 支持多Agent协作
    """
    chat_history = state.get("messages", [])
    user_query = state.get("user_input", "")
    
    # 🔴 如果有后续任务，直接执行
    if state.get("needs_followup"):
        next_action = state["needs_followup"]
        state["needs_followup"] = ""  # 清除后续任务标记
        print(f"🔄 执行后续任务: {next_action}")
        state["next_step"] = next_action
        return state
    
    llm = init_chat_model(
        model=state["config"]["model"],
        model_provider=state["config"]["model_provider"],
        dashscope_api_key=state["config"].get("DASHSCOPE_API_KEY") or os.environ.get("DASHSCOPE_API_KEY"),
        temperature=state["config"].get("temperature", 0.3)
    )
    
    if not chat_history:
        chat_history.append(HumanMessage(content=user_query))
    
    # 🔴 分析用户查询，检测复合任务
    user_lower = user_query.lower()
    
    # 🔴 检测复合任务模式
    if ("简历" in user_lower or "resume" in user_lower) and ("求职信" in user_lower or "cover letter" in user_lower):
        # 复合任务1：简历分析 + 求职信生成
        print("🎯 检测到复合任务：简历分析 + 求职信生成")
        state["needs_followup"] = "CoverLetterGenerator"
        next_action = "ResumeAnalyzer"
        
    elif ("简历" in user_lower or "resume" in user_lower or "分析我的" in user_lower) and \
         ("岗位" in user_lower or "job" in user_lower or "职位" in user_lower or "推荐" in user_lower or "招聘" in user_lower or "工作" in user_lower):
        # 🔴 复合任务2：简历分析 + 岗位推荐
        print("🎯 检测到复合任务：简历分析 + 岗位推荐")
        state["needs_followup"] = "JobSearcher"
        next_action = "ResumeAnalyzer"
        
    elif ("搜索" in user_lower or "查找" in user_lower) and \
         ("岗位" in user_lower or "job" in user_lower or "职位" in user_lower or "工作" in user_lower) and \
         ("简历" in user_lower or "resume" in user_lower or "我的" in user_lower):
        # 🔴 复合任务3：简历分析 + 岗位搜索
        print("🎯 检测到复合任务：简历分析 + 岗位搜索")
        state["needs_followup"] = "JobSearcher"
        next_action = "ResumeAnalyzer"
        
    else:
        # 单一任务，使用 supervisor chain
        supervisor_chain = get_supervisor_chain(llm)
        output = supervisor_chain.invoke({"messages": chat_history})
        next_action = output.content.strip()
        
        # 验证输出
        valid_agents = ["ResumeAnalyzer", "CoverLetterGenerator", "JobSearcher", "WebResearcher", "ChatBot", "Finish"]
        if next_action not in valid_agents:
            if any(word in user_lower for word in ["简历", "resume", "分析"]):
                next_action = "ResumeAnalyzer"
            elif any(word in user_lower for word in ["岗位", "job", "工作"]):
                next_action = "JobSearcher"
            elif any(word in user_lower for word in ["求职信", "cover letter"]):
                next_action = "CoverLetterGenerator"
            elif any(word in user_lower for word in ["搜索", "研究", "新闻"]):
                next_action = "WebResearcher"
            else:
                next_action = "ChatBot"
    
    print(f"🎯 Supervisor 路由到: {next_action}")
    state["next_step"] = next_action
    state["messages"] = chat_history
    return state

def resume_analyzer_node(state):
    """
    简历分析节点 - 支持协作模式
    """
    llm = init_chat_model(
        model=state["config"]["model"],
        model_provider=state["config"]["model_provider"],
        dashscope_api_key=state["config"].get("DASHSCOPE_API_KEY") or os.environ.get("DASHSCOPE_API_KEY"),
        temperature=state["config"].get("temperature", 0.3)
    )
    
    analyzer_agent = create_agent(
        llm, [ResumeExtractorTool(), get_google_search_results], 
        get_analyzer_agent_prompt_template()
    )
    
    state["callback"].write_agent_name("📄 ResumeAnalyzer Agent")
    
    output = analyzer_agent.invoke(
        {"messages": state["messages"]}, 
        {"callbacks": [state["callback"]]}
    )
    
    result_content = output.get("output")
    state["messages"].append(AIMessage(content=result_content, name="ResumeAnalyzer"))
    
    # 🔴 如果有后续任务，标记为未完成
    if state.get("needs_followup"):
        state["task_completed"] = False
        print("📄 简历分析完成，准备执行后续任务...")
    else:
        state["task_completed"] = True
        print("📄 简历分析完成")
    
    return state

def cover_letter_generator_node(state):
    """
    求职信生成节点 - 增强协作功能
    """
    llm = init_chat_model(
        model=state["config"]["model"],
        model_provider=state["config"]["model_provider"],
        dashscope_api_key=state["config"].get("DASHSCOPE_API_KEY") or os.environ.get("DASHSCOPE_API_KEY"),
        temperature=state["config"].get("temperature", 0.3)
    )
    
    generator_agent = create_agent(
        llm, [
            generate_letter_for_specific_job,
            save_cover_letter_for_specific_job,
            ResumeExtractorTool(),
        ], 
        get_generator_agent_prompt_template()
    )

    state["callback"].write_agent_name("✍️ CoverLetterGenerator Agent")
    
    # 🔴 检查是否有简历分析结果，如果有则生成更好的提示
    messages_to_use = state["messages"].copy()
    
    # 查找 ResumeAnalyzer 的输出
    resume_analysis = None
    for msg in reversed(state["messages"]):
        if hasattr(msg, 'name') and msg.name == "ResumeAnalyzer":
            resume_analysis = msg.content
            break
    
    if resume_analysis:
        enhanced_prompt = f"""基于以下简历分析结果，生成一份专业的求职信：

**简历分析结果：**
{resume_analysis}

请根据上述简历分析，生成一份个性化的求职信，突出候选人的关键技能和优势。"""
        
        messages_to_use.append(HumanMessage(content=enhanced_prompt))
        print("✍️ 使用简历分析结果生成求职信")
    
    output = generator_agent.invoke(
        {"messages": messages_to_use}, 
        {"callbacks": [state["callback"]]}
    )
    
    result_content = output.get("output")
    
    # 🔴 如果是协作任务的结果，添加说明
    if resume_analysis:
        final_result = f"""✍️ **基于简历分析的个性化求职信**

{result_content}

---
*此求职信基于您的简历分析结果生成，确保与您的背景和技能高度匹配*"""
    else:
        final_result = result_content
    
    state["messages"].append(AIMessage(content=final_result, name="CoverLetterGenerator"))
    state["task_completed"] = True
    print("✍️ 求职信生成完成")
    
    return state

def job_search_node(state):
    """
    职位搜索节点 - 支持协作模式
    """
    llm = init_chat_model(
        model=state["config"]["model"],
        model_provider=state["config"]["model_provider"],
        dashscope_api_key=state["config"].get("DASHSCOPE_API_KEY") or os.environ.get("DASHSCOPE_API_KEY"),
        temperature=state["config"].get("temperature", 0.3)
    )
    
    search_agent = create_agent(
        llm, [get_job_search_tool(), get_google_search_results], 
        get_search_agent_prompt_template()
    )
    
    state["callback"].write_agent_name("💼 JobSearcher Agent")
    
    # 🔴 检查是否有简历分析结果，如果有则生成更好的搜索提示
    messages_to_use = state["messages"].copy()
    
    # 查找 ResumeAnalyzer 的输出
    resume_analysis = None
    for msg in reversed(state["messages"]):
        if hasattr(msg, 'name') and msg.name == "ResumeAnalyzer":
            resume_analysis = msg.content
            break
    
    if resume_analysis:
        enhanced_prompt = f"""基于以下简历分析结果，搜索和推荐合适的岗位：

**简历分析结果：**
{resume_analysis}

请根据上述简历分析，搜索匹配的岗位机会，重点关注：
1. 与候选人技能匹配的职位
2. 适合候选人经验水平的岗位
3. 候选人所在行业或相关行业的机会
4. 提供具体的岗位列表和申请建议"""
        
        messages_to_use.append(HumanMessage(content=enhanced_prompt))
        print("💼 使用简历分析结果搜索匹配岗位")
    
    output = search_agent.invoke(
        {"messages": messages_to_use}, 
        {"callbacks": [state["callback"]]}
    )
    
    result_content = output.get("output")
    
    # 🔴 如果是协作任务的结果，添加说明
    if resume_analysis:
        final_result = f"""💼 **基于简历分析的个性化岗位推荐**

{result_content}

---
*此岗位推荐基于您的简历分析结果生成，确保与您的技能和经验高度匹配*"""
    else:
        final_result = result_content
    
    state["messages"].append(AIMessage(content=final_result, name="JobSearcher"))
    state["task_completed"] = True
    print("💼 岗位搜索完成")
    
    return state

def web_research_node(state):
    """
    网络研究节点 - 支持协作模式
    """
    llm = init_chat_model(
        model=state["config"]["model"],
        model_provider=state["config"]["model_provider"],
        dashscope_api_key=state["config"].get("DASHSCOPE_API_KEY") or os.environ.get("DASHSCOPE_API_KEY"),
        temperature=state["config"].get("temperature", 0.3)
    )
    
    research_agent = create_agent(
        llm, [get_google_search_results, scrape_website], 
        researcher_agent_prompt_template()
    )
    
    state["callback"].write_agent_name("🔍 WebResearcher Agent")
    
    output = research_agent.invoke(
        {"messages": state["messages"]}, 
        {"callbacks": [state["callback"]]}
    )
    
    state["messages"].append(AIMessage(content=output.get("output"), name="WebResearcher"))
    state["task_completed"] = True
    return state

def chatbot_node(state):
    """聊天机器人节点"""
    llm = init_chat_model(
        model=state["config"]["model"],
        model_provider=state["config"]["model_provider"],
        dashscope_api_key=state["config"].get("DASHSCOPE_API_KEY") or os.environ.get("DASHSCOPE_API_KEY"),
        temperature=state["config"].get("temperature", 0.3)
    )
    
    state["callback"].write_agent_name("🤖 ChatBot Agent")
    
    finish_chain = get_finish_chain(llm)
    output = finish_chain.invoke({"messages": state["messages"]})
    
    state["messages"].append(AIMessage(content=output.content, name="ChatBot"))
    state["task_completed"] = True
    return state

def define_graph():
    """
    定义支持多Agent协作的工作流图
    """
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("Supervisor", supervisor_node)
    workflow.add_node("ResumeAnalyzer", resume_analyzer_node)
    workflow.add_node("JobSearcher", job_search_node)
    workflow.add_node("CoverLetterGenerator", cover_letter_generator_node)
    workflow.add_node("WebResearcher", web_research_node)
    workflow.add_node("ChatBot", chatbot_node)
    
    # 设置入口点
    workflow.set_entry_point("Supervisor")
    
    # Supervisor 的条件路由
    workflow.add_conditional_edges(
        "Supervisor",
        lambda x: x["next_step"],
        {
            "ResumeAnalyzer": "ResumeAnalyzer",
            "JobSearcher": "JobSearcher", 
            "CoverLetterGenerator": "CoverLetterGenerator",
            "WebResearcher": "WebResearcher",
            "ChatBot": "ChatBot",
            "Finish": END
        }
    )
    
    # 🔴 关键改动：Agent 完成后的路由逻辑
    def should_continue(state):
        """决定Agent执行完成后是否继续"""
        if state.get("task_completed", True):
            return "END"
        else:
            return "CONTINUE"
    
    # Agent 执行完成后的条件路由
    for agent in ["ResumeAnalyzer", "JobSearcher", "CoverLetterGenerator", "WebResearcher", "ChatBot"]:
        workflow.add_conditional_edges(
            agent,
            should_continue,
            {
                "END": END,
                "CONTINUE": "Supervisor"  # 🔴 回到 Supervisor 继续协作
            }
        )
    
    return workflow.compile()

# The agent state is the input to each node in the graph
class AgentState(TypedDict):
    user_input: str              # 用户输入
    messages: list[BaseMessage]  # 对话历史
    next_step: str               # 下一步执行的Agent
    config: dict                 # 配置信息
    callback: Any                # 回调处理器
    task_completed: bool         # 🔴 新增：标记任务是否完成
    needs_followup: str          # 🔴 新增：需要后续执行的Agent