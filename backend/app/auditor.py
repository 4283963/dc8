import json
import re
import hashlib
from typing import List, Dict, Any, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_models import ChatOllama

from .schemas import Vulnerability, VulnerabilitySeverity, AuditResponse
from .vectorstore import Document


SYSTEM_PROMPT = """你是一名资深的安全审计专家，擅长分析 Java 和 C++ 代码中的安全漏洞。
请仔细分析用户提供的代码片段，找出其中的安全漏洞。

你需要关注的漏洞类型包括但不限于：
1. SQL 注入漏洞
2. 内存泄漏（C++）
3. 缓冲区溢出
4. 命令注入
5. 路径遍历
6. 不安全的反序列化
7. 敏感信息泄露
8. 空指针解引用
9. 使用已释放的内存（Use-after-free）
10. 整数溢出

对于每个发现的漏洞，请提供：
- 漏洞类型
- 严重程度（low/medium/high/critical）
- 详细描述
- 所在文件和行号（如果能确定）
- 有问题的代码片段
- 修复建议

请严格按照以下 JSON 格式输出，不要包含任何额外的解释文字：
{{
    "vulnerabilities": [
        {{
            "type": "漏洞类型名称",
            "severity": "high",
            "description": "详细描述漏洞是什么以及为什么危险",
            "file_path": "文件相对路径",
            "line_number": 42,
            "code_snippet": "有问题的代码片段",
            "suggestion": "具体的修复建议"
        }}
    ],
    "summary": "整体审计结论摘要"
}}

如果没有发现漏洞，请返回：
{{
    "vulnerabilities": [],
    "summary": "在检查的代码片段中未发现明显的安全漏洞。"
}}
"""


class SecurityAuditor:
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
                temperature=0.1,
            )
        return self._llm

    def _build_context(self, documents: List[Document]) -> str:
        context_parts = []
        for i, doc in enumerate(documents, 1):
            metadata = doc.metadata
            file_path = metadata.get("file_path", "unknown")
            line_start = metadata.get("line_start", "?")
            line_end = metadata.get("line_end", "?")
            file_type = metadata.get("file_type", "unknown")

            context_parts.append(
                f"--- 代码片段 #{i} ---\n"
                f"文件: {file_path}\n"
                f"类型: {file_type}\n"
                f"行号: {line_start}-{line_end}\n"
                f"代码:\n{doc.page_content}\n"
            )
        return "\n".join(context_parts)

    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        try:
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(response_text)
        except (json.JSONDecodeError, AttributeError):
            return {
                "vulnerabilities": [],
                "summary": f"解析 LLM 响应失败。原始响应:\n{response_text[:500]}"
            }

    def _generate_vuln_id(self, vuln_data: Dict) -> str:
        raw = f"{vuln_data.get('file_path', '')}:{vuln_data.get('line_number', '')}:{vuln_data.get('type', '')}"
        return hashlib.md5(raw.encode()).hexdigest()[:8]

    def audit(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 5,
    ) -> AuditResponse:
        if not documents:
            return AuditResponse(
                query=query,
                vulnerabilities=[],
                total_found=0,
                summary="未找到相关代码片段进行审计。请先确保已扫描项目。",
            )

        context = self._build_context(documents)

        user_prompt = f"""用户查询: {query}

相关代码片段:
{context}

请基于以上代码片段进行安全审计，按照指定的 JSON 格式输出结果。"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", user_prompt),
        ])

        chain = prompt | self.llm | StrOutputParser()
        response_text = chain.invoke({})

        result = self._parse_llm_response(response_text)

        vulnerabilities = []
        for vuln_data in result.get("vulnerabilities", []):
            try:
                severity = vuln_data.get("severity", "medium").lower()
                if severity not in [s.value for s in VulnerabilitySeverity]:
                    severity = "medium"

                vuln = Vulnerability(
                    id=self._generate_vuln_id(vuln_data),
                    type=vuln_data.get("type", "Unknown"),
                    severity=VulnerabilitySeverity(severity),
                    description=vuln_data.get("description", ""),
                    file_path=vuln_data.get("file_path", ""),
                    line_number=vuln_data.get("line_number"),
                    code_snippet=vuln_data.get("code_snippet", ""),
                    suggestion=vuln_data.get("suggestion", ""),
                )
                vulnerabilities.append(vuln)
            except Exception as e:
                continue

        return AuditResponse(
            query=query,
            vulnerabilities=vulnerabilities,
            total_found=len(vulnerabilities),
            summary=result.get("summary", ""),
        )
