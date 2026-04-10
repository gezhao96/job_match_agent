# Job Match Agent (LangChain 初版)

一个可运行的 LangChain 项目初版：

- 自然语言输入招聘网址 + 求职偏好
- 自动抓取招聘网站列表页或详情页
- 提取岗位结构化信息
- 用 LLM 做岗位匹配评分
- 输出 Markdown 推荐报告

## 1. 安装

```bash
cd job_match_agent
python -m venv .venv
source .venv/bin/activate   # Windows 用 .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

填写 `.env`：

```env
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
# OPENAI_BASE_URL=...
```

## 2. 运行

### 方式 A：交互输入

```bash
python app.py
```

示例输入：

```text
请帮我分析这个招聘网站里适合我的岗位：
https://job.hust.edu.cn/zpxx123123/index.htm

我的求职方向是光纤传感、光电信息、AI算法、智能感知；
希望工作地在上海、深圳、杭州、武汉；
学历是博士；
优先考虑高校、研究院或技术研发类岗位；
不考虑销售、行政和纯运维类岗位。
```

### 方式 B：命令行参数

```bash
python app.py --input-file sample_input.txt --max-jobs 12 --max-pages 3
```

## 3. 输出

运行后会生成：

- `outputs/crawled_jobs.json`：原始抓取结果
- `outputs/structured_jobs.json`：结构化岗位数据
- `outputs/match_results.json`：匹配评分结果
- `outputs/reports/latest_report.md`：最终推荐报告

## 4. 当前版本说明

这是一个 **MVP 初版**，优先保证结构清晰和可运行：

- 爬虫：`requests + BeautifulSoup`
- LLM：`langchain-openai` 的 `ChatOpenAI`
- 结构化输出：`with_structured_output(PydanticModel)`
- 工作流：LangChain 链式编排 + 可扩展工具化模块

如果你后续要进一步做成更“Agent”的版本，可以把 `tools/` 下能力封装成 LangChain tools，再接 `create_tool_calling_agent` 或 LangGraph。

## 5. 已知限制

1. 动态渲染网站、登录网站、验证码网站，可能需要接入 Playwright。
2. 列表页抓取依赖启发式规则，最好根据目标站点再调一下关键词。
3. 大模型评分是“规则 + 语义”混合，不应代替最终人工决策。
