# JobPilot Assistant（多智能体求职助手）

> 利用多智能体协同与检索/生成式 AI，辅助求职全流程：职位发现 → 简历解析 → 公司/行业调研 → 求职信生成 → 交互式策略咨询。

<img src="multiagent.png" alt="系统架构示意（Supervisor 调度多个功能型智能体：搜索 / 简历解析 / 求职信生成 / 调研 / 对话）" width="560">

## 目录
- [演示 Demo](#演示-demo)
- [项目动机与价值](#项目动机与价值)
- [功能总览](#功能总览)
- [系统架构](#系统架构)
- [组件说明](#组件说明)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [环境变量与配置](#环境变量与配置)
- [使用指南](#使用指南)
- [数据与流程示例](#数据与流程示例)
- [目录结构](#目录结构)
- [性能与扩展建议](#性能与扩展建议)
- [常见问题 FAQ / 故障排查](#常见问题-faq--故障排查)
- [Roadmap](#roadmap)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

## 演示 Demo
https://github.com/user-attachments/assets/f1e191ae-19c4-48a0-b24f-dfd59bd9240a

## 项目动机与价值
招聘平台碎片化 + 岗位文本非结构化 + 求职材料同质化 → 决策与准备成本高。  
本项目通过多智能体管道降低以下成本：检索过滤、认知提炼、材料生成、策略对话。

## 功能总览
| 模块 | 说明 | 价值 |
| ---- | ---- | ---- |
| 智能职位搜索 | 行业 / 技能 / 地域过滤（可扩展适配器） | 降低初筛时间 |
| 简历解析 | 抽取技能、经历、成就要点 | 结构化供后续复用 |
| 求职信生成 | 岗位 JD + 解析简历上下文 | 定制化表达 |
| 公司 / 行业调研 | 搜索 + 网页抓取聚合 | 快速获取背景摘要 |
| 多轮对话策略 | 可追问 / 生成优化建议 | 减少重复输入 |
| 可扩展工具层 | 插入自定义 Tool / 数据源 | 模块化扩展 |

## 系统架构
Supervisor（调度）根据会话意图调用特定功能智能体：
- JobSearcher
- ResumeAnalyzer
- CoverLetterGenerator
- WebResearcher
- ChatBot  
编排采用 LangGraph，支持状态可视化与后续拓扑扩展（分支 / 循环 / 审批节点）。

## 组件说明
- Agent 统一工厂：封装提示模版、工具注入、记忆配置
- Tools：职位检索、网页抓取、简历解析
- 消息上下文共享：避免重复解析 & 丢失历史
- 前端：Streamlit（文件上传 + 对话 + 结果下载）

## 技术栈
- LangGraph / LangChain
- OpenAI / Groq / 通义千问（可切换）
- Serper（搜索）+ Firecrawl（网页正文提炼）
- Streamlit UI
- 可选：LinkedIn 第三方 Python 接口（若法律合规）

## 快速开始
```bash
git clone https://github.com/chenchong911/JobPilot-Multi-agent
cd JobPilot-CareerAssistant-Multiagent
python -m venv venv && source venv/bin/activate   # 或 conda create -n jobpilot python=3.10
pip install -r requirements.txt
streamlit run app.py
```
访问地址（默认）: http://localhost:8501

## 环境变量与配置
在 .streamlit/secrets.toml 中填写（不提交到版本库）：
```toml
OPENAI_API_KEY = ""
GROQ_API_KEY = ""
DASHSCOPE_API_KEY = ""         # 通义千问（可选）
SERPER_API_KEY = ""
FIRECRAWL_API_KEY = ""
LANGCHAIN_API_KEY = ""         # 用 LangSmith 追踪时
LANGCHAIN_TRACING_V2 = "true"
LANGCHAIN_PROJECT = "JOB_SEARCH_AGENT"
LINKEDIN_JOB_SEARCH = "linkedin_api"
LINKEDIN_EMAIL = ""
LINKEDIN_PASS = ""
```
未配置的键会降级为仅能执行本地对话（或提示缺失）。

## 使用指南
1. 上传 PDF 简历（未上传则尝试使用内置示例 dummy_resume.pdf）
2. 输入请求示例：
   - “找深圳嵌入式 C++ 驱动开发岗位，偏车规”
   - “用第 2 个岗位生成中文求职信”
   - “根据我的简历帮我提炼 5 条量化成就”
   - “调研字节跳动在 AI Infra 近期布局”
3. 选择或 refine 结果（继续追加条件：薪资 / 规模 / 技术栈）
4. 生成求职信 & 下载
5. 进行策略问答（谈薪、JD 要点比对等）

## 数据与流程示例
请求：生成求职信  
1) Supervisor 识别意图 → 需要简历摘要 + JD  
2) 若无缓存调用 ResumeAnalyzer  
3) 调用 CoverLetterGenerator 组装模版 + 动态要点  
4) 返回结构（引言 / 匹配亮点 / 项目与成果 / 结语）

## 目录结构
```
app.py                      # 入口
agents/                     # 智能体定义
tools/                      # 自定义工具（检索/抓取/解析）
graphs/                     # LangGraph 编排
prompts/                    # 提示模版
temp/                       # 运行期简历缓存（自动创建）
```

## 性能与扩展建议
- 缓存策略：可接入 Redis / sqlite 保存解析结果（Key: 文件哈希）
- 模型切换：低成本草稿用 qwen-turbo / gpt-4o-mini，最终文案高阶模型
- 增量扩展：新增 Tool 只需在工厂注册 + Supervisor 路由规则
- 内容精炼：提示里统一要求“结构化返回 JSON”再转前端展示（可后续改造）

## 常见问题 FAQ / 故障排查
Q: ModuleNotFoundError: streamlit_analytics2  
A: 改为安装 streamlit-analytics，或使用可选导入模式。  
Q: 无法调用 LinkedIn  
A: 确认第三方包合法可用 & 环境变量 LINKEDIN_EMAIL / PASS 已设置。  
Q: Firecrawl 403  
A: 检查额度 / Key；可降级仅搜索摘要。  
Q: 求职信生成缺少项目亮点  
A: 确认简历 PDF 可被正确 OCR/解析，必要时手动补充“我的关键项目：...”。

## Roadmap
- [ ] 多简历版本自动匹配岗位差异
- [ ] 项目成就量化建议器（Auto Achievement Rewriter）
- [ ] 技能差距分析 + 学习路径推荐
- [ ] RAG 企业知识库（融资/团队/技术栈）
- [ ] 一键导出多格式（Markdown / PDF / DOCX）
- [ ] 职位结果评分（匹配度 + 置信度解释）
- [ ] 批量岗位 → 批量求职信队列生成
- [ ] 可视化流图（Graph Inspector 集成）

## 贡献指南
1. Fork & 新建分支：feature/xxx 或 fix/xxx  
2. 运行 pre-check（可自建脚本：格式化 + lint）  
3. 提交信息遵循规范：feat / fix / docs / chore / refactor  
4. 发 PR，描述目的 + 截图（如为前端改动）  

建议：附测试用例（若涉及解析/格式化功能）。

## 许可证
MIT License，详见 [LICENSE](LICENSE)。

## 隐私与合规
- 不持久保存上传简历（仅运行期 temp/，可自行清理或配置 ignore）
- 请勿将真实敏感数据提交到公共仓库
- 第三方数据源使用需符合其服务条款

## 致谢
受多智能体编排与检索增强生成（RAG）方案启发，欢迎社区继续扩展更多职业发展辅助功能。

---
欢迎 Issue / PR / Star 支持项目发展。