# JobPilot Assistant（多智能体求职助手）

<img src="multiagent.png" alt="系统架构示意" width="500">


JobPilot Assistant 是一个基于多智能体（Multi-Agent）架构的智能求职辅助系统，旨在利用生成式 AI 与任务协同机制，帮助求职者更高效地进行职位搜索、简历解析、公司调研与个性化求职文案生成。

## 目录

- [演示 Demo](#演示-demo)
- [为什么需要它](#为什么需要它)
- [核心功能](#核心功能)
- [架构概览](#架构概览)
- [关键组件](#关键组件)
- [使用的技术](#使用的技术)
- [安装部署](#安装部署)
- [使用指南](#使用指南)
- [未来规划](#未来规划)
- [参与贡献](#参与贡献)
- [许可证](#许可证)

## 演示 Demo
https://github.com/user-attachments/assets/f1e191ae-19c4-48a0-b24f-dfd59bd9240a

## 为什么需要它

当前就业市场节奏快、信息量大，求职者常面临：
- 难以快速筛选与自身背景匹配的岗位
- 求职材料（求职信/自我陈述）个性化不足
- 缺乏对目标公司的结构化调研
- 多个平台与步骤割裂、效率低下

本项目通过多智能体协作解决：
- 按行业 / 技能 / 地域定制职位搜索
- 自动生成针对岗位定制的求职信
- 抓取并提炼公司背景、业务与机会
- 分析简历要点，辅助匹配与优化
- 统一对话式交互，减少上下文重复输入

## 核心功能

- **智能职位搜索**：基于关键词、地点、技能过滤（可扩展对接 LinkedIn 等接口）。
- **简历解析（Resume Analysis）**：抽取技能、项目、成就信息，用于后续匹配与文案生成。
- **个性化求职信生成**：结合岗位描述 + 简历要点动态生成。
- **公司/行业调研**：通过搜索与抓取工具（Serper + FireCrawl）汇总信息。
- **多轮对话助手**：提供通用问答，支持策略性求职咨询。
- **可扩展工具层**：通过自定义 Tool 接口添加新的检索、抓取或外部 API。

## 架构概览

系统基于“监督者 + 专职智能体”模型：
- **Supervisor（调度智能体）**：根据当前上下文与目标任务决定调用哪个子智能体。
- **JobSearcher**：职位搜索与过滤。
- **ResumeAnalyzer**：解析上传的 PDF 简历内容（提取技能/经验）。
- **CoverLetterGenerator**：生成岗位定制化求职信。
- **WebResearcher**：公司 / 竞争对手 / 行业背景调研。
- **ChatBot**：处理通用问题与解释系统输出。

数据与控制流由 LangGraph 编排，支持可视化与调试（可接入 LangSmith 追踪）。

## 关键组件

- **统一 Agent 创建函数**：规范工具注入、提示词模版、记忆配置。
- **自定义工具 (Tools)**：如职位搜索工具、简历解析器、网页抓取工具等。
- **上下文消息流**：多智能体共享必要上下文，避免信息丢失。
- **Streamlit 前端**：提供文件上传、对话交互、结果展示与下载。

## 使用的技术

- **LangGraph**：多智能体工作流编排。
- **Streamlit**：轻量交互式前端。
- **OpenAI / GROQ API**：LLM 推理。
- **SerperClient + FireCrawlClient**：搜索 + 网页内容抓取。
- （可选）**LinkedIn API（第三方 Python 包）**：职位数据源。

## 安装部署

1. 克隆仓库：
   ```bash
   git clone https://github.com/amanv1906/GENAI-CareerAssistant-Multiagent.git
   cd GENAI-CareerAssistant-Multiagent
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 配置环境（创建 `.streamlit/secrets.toml`）：
   ```toml
   OPENAI_API_KEY = "你的 OpenAI Key"
   LANGCHAIN_API_KEY = "" # 如需用 LangSmith 追踪可填
   LANGCHAIN_TRACING_V2 = "true"
   LANGCHAIN_PROJECT = "JOB_SEARCH_AGENT"
   GROQ_API_KEY = "Groq 模型 Key（可选）"
   SERPER_API_KEY = "Serper 搜索 Key"
   FIRECRAWL_API_KEY = "Firecrawl 抓取 Key"
   LINKEDIN_JOB_SEARCH = "linkedin_api" # 启用 LinkedIn 搜索时设置
   LINKEDIN_EMAIL = "" # 启用 LinkedIn 搜索需填写
   LINKEDIN_PASS = ""
   ```

4. 启动应用：
   ```bash
   streamlit run app.py
   ```

## 使用指南

1. 上传 PDF 简历（Resume）  
2. 在聊天框输入需求（如：“帮我找上海的数据分析岗” / “生成这份岗位的求职信”）  
3. 根据返回结果继续追问或 refine 条件  
4. 下载生成的求职信或分析结果  
5. 可组合使用：先搜索岗位 -> 选择一个岗位描述 -> 生成定制求职信  

## 目录结构（简述）

（如下为典型模式，实际按仓库为准）
```
app.py                # Streamlit 入口
agents/               # 各类智能体与工具封装
tools/                # 自定义工具实现
graphs/               # LangGraph 工作流/状态管理
prompts/              # 提示词模板
```

## 未来规划

- 一键投递与主流招聘平台 API 集成  
- 增强对中文职位数据支持  
- 增加职业路径推荐与技能差距分析  
- 引入向量检索（RAG）增强公司与行业背景回答  
- 支持多简历版本智能管理  

## 参与贡献

欢迎提交 Issue / PR：
- 优化提示词 / Agent 策略
- 增加新的职位来源适配器
- 添加国际化（i18n）
- 性能与缓存策略改进

提交流程：
1. Fork 仓库
2. 新建分支：feature/xxx 或 fix/xxx
3. PR 并描述变更动机

## 许可证

本项目基于 MIT License 开源，详见 [LICENSE](LICENSE)。

---

如需英文版可参考初始提交历史。欢迎改进。