import json
import os
import re
from typing import Optional, Dict, Any

from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain.agents import (
    create_tool_calling_agent,
    AgentExecutor,
)
from langchain_community.chat_models import ChatOllama

from .file_tools import FileToolkit
from .schemas import RepairRequest, RepairResult


SYSTEM_PROMPT = """你是一名资深的代码安全修复专家。你的任务是修复用户指出的代码安全漏洞。

你必须遵循以下工作流程：
1. 首先，使用 read_file 工具读取有漏洞的完整文件内容（或指定行范围）
2. 仔细分析漏洞位置和上下文代码
3. 生成修复后的代码
4. 使用 replace_lines 或 write_file 工具将修复后的代码写回文件
5. 验证修复是否成功

严格遵守以下规则：
- 修复时保持原代码的缩进、风格和编码习惯
- 只修改有漏洞的部分，不要无关改动
- 对于 Java SQL 注入，必须使用 PreparedStatement 替换字符串拼接
- 对于 C++ 内存泄漏，确保正确释放内存
- 对于缓冲区溢出，使用安全的字符串操作函数
- 每次修改前自动创建 .bak 备份文件
- 修复完成后必须验证结果

在你的最终回答中，用简洁的语言告诉用户：
1. 修复了什么类型的漏洞
2. 做了什么具体改动（例如："改用 PreparedStatement"）
3. 备份文件的位置
"""


USER_PROMPT_TEMPLATE = """请修复以下安全漏洞：

漏洞信息：
- 漏洞类型: {vuln_type}
- 严重程度: {severity}
- 文件路径: {file_path}
- 行号: {line_number}
- 漏洞描述: {description}
- 有问题的代码片段:
```
{code_snippet}
```
- 修复建议: {suggestion}

项目根目录: {project_root}
"""


FINAL_ANSWER_FORMAT = """修复完成！

漏洞类型：{vuln_type}
文件路径：{file_path}

修改说明：
{changes_description}

已为您自动修复{fix_detail}。
备份文件：{backup_path}
"""


class RepairAgent:
    def __init__(
        self,
        ollama_base_url: str = "http://localhost:11434",
        model_name: str = "qwen2.5:7b",
    ):
        self.ollama_base_url = ollama_base_url
        self.model_name = model_name
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = ChatOllama(
                base_url=self.ollama_base_url,
                model=self.model_name,
                temperature=0.2,
                format="json",
            )
        return self._llm

    def _build_tools(self, file_toolkit: FileToolkit):
        @tool
        def read_file(relative_path: str, line_start: Optional[int] = None, line_end: Optional[int] = None) -> str:
            """读取项目中指定文件的内容。可选择指定行号范围。

            Args:
                relative_path: 相对于项目根目录的文件路径，例如 'src/main/java/MyClass.java'
                line_start: 起始行号（从1开始，包含），可选
                line_end: 结束行号（从1开始，包含），可选
            """
            result = file_toolkit.read_file(relative_path, line_start, line_end)
            return json.dumps(result, ensure_ascii=False, indent=2)

        @tool
        def replace_lines(relative_path: str, line_start: int, line_end: int, new_content: str) -> str:
            """替换文件中指定行范围的内容。会自动创建备份文件。

            Args:
                relative_path: 相对于项目根目录的文件路径
                line_start: 起始行号（从1开始，包含）
                line_end: 结束行号（从1开始，包含）
                new_content: 替换后的新内容，可以是多行
            """
            result = file_toolkit.replace_lines(
                relative_path, line_start, line_end, new_content, backup=True
            )
            return json.dumps(result, ensure_ascii=False, indent=2)

        @tool
        def write_file(relative_path: str, content: str) -> str:
            """覆盖写入整个文件。会自动创建备份文件。

            Args:
                relative_path: 相对于项目根目录的文件路径
                content: 要写入的完整文件内容
            """
            result = file_toolkit.write_file(relative_path, content, backup=True)
            return json.dumps(result, ensure_ascii=False, indent=2)

        @tool
        def list_directory(relative_path: str = ".") -> str:
            """列出目录内容。

            Args:
                relative_path: 相对于项目根目录的目录路径，默认为根目录
            """
            result = file_toolkit.list_dir(relative_path)
            return json.dumps(result, ensure_ascii=False, indent=2)

        return [read_file, replace_lines, write_file, list_directory]

    def _build_agent_executor(self, file_toolkit: FileToolkit) -> AgentExecutor:
        tools = self._build_tools(file_toolkit)

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(
            llm=self.llm,
            tools=tools,
            prompt=prompt,
        )

        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=10,
            handle_parsing_errors=True,
        )

    def repair(self, request: RepairRequest) -> RepairResult:
        """执行智能修复。"""
        try:
            normalized_project_path = request.project_path.replace("\\", "/")
            normalized_file_path = request.file_path.replace("\\", "/")

            file_toolkit = FileToolkit(normalized_project_path)

            line_start = None
            line_end = None
            if request.line_number:
                line_start = max(1, request.line_number - 10)
                line_end = request.line_number + 30

            read_result = file_toolkit.read_file(
                normalized_file_path,
                line_start=line_start,
                line_end=line_end,
            )

            if not read_result.get("success"):
                return RepairResult(
                    success=False,
                    message=f"读取文件失败: {read_result.get('error', '未知错误')}",
                )

            original_code = read_result.get("content", "")
            total_lines = read_result.get("total_lines", 0)

            agent_executor = self._build_agent_executor(file_toolkit)

            line_info = ""
            if request.line_number:
                line_info = f"约第 {request.line_number} 行"

            user_input = USER_PROMPT_TEMPLATE.format(
                vuln_type=request.vulnerability_type,
                severity="",
                file_path=normalized_file_path,
                line_number=line_info,
                description=request.description,
                code_snippet=request.code_snippet,
                suggestion=request.suggestion,
                project_root=normalized_project_path,
            )

            agent_result = agent_executor.invoke({"input": user_input})
            agent_output = str(agent_result.get("output", ""))

            backup_path = self._extract_backup_path(agent_output) or self._find_backup_file(
                normalized_project_path, normalized_file_path
            )

            read_after = file_toolkit.read_file(normalized_file_path)
            repaired_code = read_after.get("content", "") if read_after.get("success") else None

            changes_description = self._extract_changes_description(
                agent_output,
                request.vulnerability_type,
            )

            success = "修复完成" in agent_output or "已修复" in agent_output or "成功" in agent_output or \
                      (repaired_code is not None and repaired_code != original_code)

            if not backup_path and success:
                backup_path = self._find_backup_file(normalized_project_path, normalized_file_path)

            return RepairResult(
                success=success,
                message=changes_description,
                original_code=original_code,
                repaired_code=repaired_code,
                backup_path=backup_path,
                changes_applied=changes_description,
            )

        except Exception as e:
            return RepairResult(
                success=False,
                message=f"修复过程中发生错误: {str(e)}",
            )

    def _extract_backup_path(self, text: str) -> Optional[str]:
        match = re.search(r'备份文件[：:]\s*([^\s，,。\n]+)', text)
        if match:
            return match.group(1)

        match = re.search(r'backup_path[":\s]+([^\s",}\n]+)', text)
        if match:
            path = match.group(1).strip('"')
            return path if path != "null" else None

        return None

    def _find_backup_file(self, project_root: str, file_path: str) -> Optional[str]:
        try:
            backup_path = os.path.join(project_root, file_path + ".bak")
            if os.path.exists(backup_path):
                return backup_path.replace("\\", "/")
        except Exception:
            pass
        return None

    def _extract_changes_description(self, agent_output: str, vuln_type: str) -> str:
        if "PreparedStatement" in agent_output or "预编译" in agent_output:
            return f"已修复 {vuln_type} 漏洞，将字符串拼接 SQL 改为使用 PreparedStatement 参数化查询，避免了 SQL 注入风险。"

        if "内存泄漏" in vuln_type or "memory leak" in agent_output.lower():
            return f"已修复 {vuln_type} 漏洞，添加了正确的内存释放逻辑（delete/delete[]），防止资源泄漏。"

        if "缓冲区溢出" in vuln_type or "buffer overflow" in agent_output.lower():
            return f"已修复 {vuln_type} 漏洞，改用安全的字符串操作（如 strncpy_s、std::string），限制写入长度。"

        if "命令注入" in vuln_type or "command injection" in agent_output.lower():
            return f"已修复 {vuln_type} 漏洞，避免直接将用户输入拼接到系统命令中，改用参数化调用或白名单校验。"

        if "路径遍历" in vuln_type or "path traversal" in agent_output.lower():
            return f"已修复 {vuln_type} 漏洞，对用户输入的文件名进行规范化和安全校验，限制访问范围。"

        lines = [line.strip() for line in agent_output.strip().split("\n") if line.strip()]
        if lines:
            return lines[-1]

        return f"已修复 {vuln_type} 漏洞。"
