from pydantic import BaseModel
from typing import List, Optional
from enum import Enum


class ScanRequest(BaseModel):
    project_path: str
    file_types: List[str] = ["java", "cpp"]


class ScanResponse(BaseModel):
    status: str
    total_files: int
    total_chunks: int
    message: str


class AuditRequest(BaseModel):
    query: str
    top_k: int = 5


class VulnerabilitySeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Vulnerability(BaseModel):
    id: str
    type: str
    severity: VulnerabilitySeverity
    description: str
    file_path: str
    line_number: Optional[int] = None
    code_snippet: str
    suggestion: str


class AuditResponse(BaseModel):
    query: str
    vulnerabilities: List[Vulnerability]
    total_found: int
    summary: str
