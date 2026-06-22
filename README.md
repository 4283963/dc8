# CodeShield - 智能代码安全审计工具

基于 RAG（检索增强生成）技术的本地代码安全审计系统，支持 Java 和 C++ 代码的智能化安全漏洞检测。

## 功能特性

- 🔍 **本地代码扫描**：递归扫描 Java 和 C/C++ 源文件
- 🧩 **智能代码切块**：基于行数的智能分块，保留代码上下文
- 📚 **向量数据库**：使用 ChromaDB 存储代码 Embedding
- 🤖 **AI 安全审计**：基于 LLM 的智能漏洞分析
- 🎯 **多种漏洞检测**：SQL 注入、内存泄漏、缓冲区溢出、命令注入等
- 💻 **简洁 Web 界面**：基于 Astro 的现代化前端
- 🔒 **本地运行**：所有数据在本地处理，保护代码隐私

## 架构概览

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Astro 前端    │────▶│  FastAPI 后端   │────▶│  Chroma 向量库   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                  │
                                  ▼
                          ┌─────────────────┐
                          │   LangChain     │
                          │   RAG 工作流    │
                          └─────────────────┘
                                  │
                                  ▼
                          ┌─────────────────┐
                          │   Ollama LLM    │
                          │  (本地大模型)   │
                          └─────────────────┘
```

## 目录结构

```
dc8/
├── backend/                 # Python 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py         # FastAPI 主入口
│   │   ├── scanner.py      # 代码扫描与切块
│   │   ├── vectorstore.py  # Chroma 向量存储
│   │   ├── auditor.py      # RAG 安全审计
│   │   └── schemas.py      # Pydantic 数据模型
│   ├── requirements.txt
│   └── .env.example
├── frontend/                # Astro 前端
│   ├── src/
│   │   └── pages/index.astro
│   ├── public/
│   │   ├── styles/global.css
│   │   └── scripts/app.js
│   ├── package.json
│   └── astro.config.mjs
├── sample-code/             # 测试样例代码
│   ├── java/
│   └── cpp/
└── scripts/                 # 启动脚本
    ├── start-backend.sh
    └── start-frontend.sh
```

## 环境要求

### 后端
- Python 3.10+
- pip / venv

### 前端
- Node.js 18+
- npm

### LLM（必需）
- [Ollama](https://ollama.ai/) - 本地大模型运行时
- 推荐模型：`qwen2.5:7b` 或 `llama3.1:8b`

## 快速开始

### 1. 安装 Ollama

```bash
# macOS
brew install ollama

# 或从官网下载: https://ollama.ai/
```

拉取推荐模型：

```bash
ollama pull qwen2.5:7b
```

### 2. 启动后端服务

```bash
cd dc8

# 方式一：使用启动脚本
./scripts/start-backend.sh

# 方式二：手动启动
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

后端服务将在 `http://localhost:8000` 启动。

API 文档：`http://localhost:8000/docs`

### 3. 启动前端服务

```bash
# 方式一：使用启动脚本
./scripts/start-frontend.sh

# 方式二：手动启动
cd frontend
npm install
npm run dev
```

前端界面将在 `http://localhost:4321` 启动。

### 4. 使用工具

1. 打开浏览器访问 `http://localhost:4321`
2. 在"项目目录路径"中输入要审计的项目绝对路径（例如 `./sample-code`）
3. 选择要扫描的文件类型（Java / C++）
4. 点击"开始扫描"，等待代码索引完成
5. 在审计查询中输入问题，例如：
   - "帮我审计这个项目有哪些 SQL 注入风险"
   - "检查是否存在内存泄漏"
   - "全面安全审计"
6. 点击"开始审计"，查看漏洞报告

## API 接口

### `GET /api/health`
健康检查

### `POST /api/scan`
扫描并索引项目代码

请求体：
```json
{
  "project_path": "/path/to/project",
  "file_types": ["java", "cpp"]
}
```

### `POST /api/audit`
执行安全审计

请求体：
```json
{
  "query": "检查 SQL 注入漏洞",
  "top_k": 5
}
```

## 支持的漏洞类型

| 类型 | Java | C++ |
|------|------|-----|
| SQL 注入 | ✅ | - |
| 内存泄漏 | - | ✅ |
| 缓冲区溢出 | - | ✅ |
| 命令注入 | ✅ | ✅ |
| 路径遍历 | ✅ | ✅ |
| Use-after-free | - | ✅ |
| 双重释放 | - | ✅ |
| 空指针解引用 | ✅ | ✅ |
| 整数溢出 | - | ✅ |
| 敏感信息泄露 | ✅ | ✅ |
| 不安全的反序列化 | ✅ | - |

## 配置说明

### 环境变量（后端）

复制 `.env.example` 为 `.env` 并修改：

```bash
cd backend
cp .env.example .env
```

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 服务地址 |
| `OLLAMA_MODEL` | `qwen2.5:7b` | 使用的 LLM 模型名称 |
| `CHROMA_PERSIST_DIR` | `./data/chroma_db` | 向量数据库存储路径 |

### 模型选择建议

| 模型 | 参数量 | 速度 | 质量 | 推荐场景 |
|------|--------|------|------|----------|
| `qwen2.5:7b` | 7B | 快 | 好 | 日常使用 |
| `llama3.1:8b` | 8B | 中 | 好 | 英文为主 |
| `qwen2.5:14b` | 14B | 慢 | 优 | 复杂审计 |

## 测试样例

项目包含了带有典型漏洞的测试代码，位于 `sample-code/` 目录：

- `sample-code/java/UserService.java` - SQL 注入、命令注入、路径遍历、敏感信息泄露
- `sample-code/cpp/DataProcessor.cpp` - 内存泄漏、缓冲区溢出、Use-after-free、双重释放

快速测试：

```bash
# 扫描测试代码
curl -X POST http://localhost:8000/api/scan \
  -H "Content-Type: application/json" \
  -d '{"project_path": "./sample-code", "file_types": ["java", "cpp"]}'

# 执行审计
curl -X POST http://localhost:8000/api/audit \
  -H "Content-Type: application/json" \
  -d '{"query": "检查SQL注入和内存泄漏漏洞"}'
```

## 工作原理

### 扫描阶段
1. 递归遍历项目目录，收集 .java / .cpp 等源文件
2. 将每个文件按行数智能切块（默认 80 行一块，20 行重叠）
3. 使用 sentence-transformers (all-MiniLM-L6-v2) 生成 Embedding
4. 将代码块和元数据存入 Chroma 向量数据库

### 审计阶段
1. 接收用户的审计查询
2. 将查询向量化，在向量库中检索最相关的 Top-K 代码块
3. 将代码块和查询组装成 Prompt，发送给本地 LLM
4. 解析 LLM 返回的 JSON 格式漏洞报告
5. 前端展示漏洞详情和修复建议

## 常见问题

### Q: 第一次启动很慢？
A: 首次运行会下载 Embedding 模型 (all-MiniLM-L6-v2, 约 80MB)，请耐心等待。

### Q: 如何更换 LLM 模型？
A: 修改后端 `.env` 文件中的 `OLLAMA_MODEL` 变量，或设置环境变量。确保已通过 `ollama pull` 拉取对应模型。

### Q: 支持哪些编程语言？
A: 当前主要针对 Java 和 C/C++。可以通过修改 `scanner.py` 中的 `SUPPORTED_EXTENSIONS` 扩展支持更多语言。

### Q: 向量数据存在哪里？
A: 默认存储在 `backend/data/chroma_db/` 目录下。删除该目录即可清除所有索引数据。

## 许可证

MIT License
