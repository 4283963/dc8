import os
import hashlib
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import (
    ScanRequest,
    ScanResponse,
    AuditRequest,
    AuditResponse,
    RepairRequest,
    RepairResponse,
)
from .scanner import CodeScanner
from .vectorstore import VectorStore
from .auditor import SecurityAuditor
from .repair_agent import RepairAgent


_vectorstore: VectorStore = None
_auditor: SecurityAuditor = None
_repair_agent: RepairAgent = None
_current_project_id: str = "default"
_current_project_path: str = ""


def get_vectorstore() -> VectorStore:
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = VectorStore()
    return _vectorstore


def get_auditor() -> SecurityAuditor:
    global _auditor
    if _auditor is None:
        _auditor = SecurityAuditor(
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model_name=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
        )
    return _auditor


def get_repair_agent() -> RepairAgent:
    global _repair_agent
    if _repair_agent is None:
        _repair_agent = RepairAgent(
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model_name=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
        )
    return _repair_agent


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/")


def _path_to_project_id(path: str) -> str:
    normalized = _normalize_path(path)
    return hashlib.md5(normalized.encode()).hexdigest()[:12]


app = FastAPI(
    title="智能代码安全审计工具",
    description="基于 RAG 的本地代码安全审计系统",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "安全审计服务运行中"}


@app.post("/api/scan", response_model=ScanResponse)
async def scan_project(request: ScanRequest):
    global _current_project_id
    try:
        normalized_path = _normalize_path(request.project_path)
        scanner = CodeScanner(normalized_path, request.file_types)
        chunks, total_files = scanner.chunk_all_files()

        if not chunks:
            return ScanResponse(
                status="warning",
                total_files=0,
                total_chunks=0,
                message=f"在 {normalized_path} 中未找到支持的代码文件",
            )

        vs = get_vectorstore()
        project_id = _path_to_project_id(normalized_path)
        _current_project_id = project_id
        _current_project_path = normalized_path
        total_indexed = vs.index_chunks(chunks, project_id=project_id)

        return ScanResponse(
            status="success",
            total_files=total_files,
            total_chunks=total_indexed,
            message=f"成功扫描 {total_files} 个文件，生成 {total_indexed} 个代码块",
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except NotADirectoryError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"扫描失败: {str(e)}")


@app.post("/api/audit", response_model=AuditResponse)
async def audit_project(request: AuditRequest):
    try:
        vs = get_vectorstore()
        auditor = get_auditor()

        project_id = _current_project_id
        if not vs.has_index(project_id):
            raise HTTPException(
                status_code=400,
                detail="尚未扫描任何项目。请先调用 /api/scan 扫描代码。",
            )

        docs = vs.similarity_search(
            query=request.query,
            k=request.top_k,
            project_id=project_id,
        )

        result = auditor.audit(
            query=request.query,
            documents=docs,
            top_k=request.top_k,
        )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"审计失败: {str(e)}")


@app.get("/api/projects/{project_id}/has-index")
async def has_index(project_id: str):
    vs = get_vectorstore()
    return {"has_index": vs.has_index(project_id)}


@app.post("/api/repair", response_model=RepairResponse)
async def repair_vulnerability(request: RepairRequest):
    try:
        project_path = _normalize_path(request.project_path) if request.project_path else _current_project_path
        if not project_path:
            raise HTTPException(
                status_code=400,
                detail="未指定项目路径，请先扫描项目或在请求中提供 project_path",
            )

        request_data = request.model_dump()
        request_data["project_path"] = project_path
        request_data["file_path"] = _normalize_path(request.file_path)

        from .schemas import RepairRequest
        normalized_request = RepairRequest(**request_data)

        agent = get_repair_agent()
        result = agent.repair(normalized_request)

        if result.success:
            return RepairResponse(
                vulnerability_id=request.vulnerability_id,
                status="success",
                result=result,
            )
        else:
            return RepairResponse(
                vulnerability_id=request.vulnerability_id,
                status="failed",
                result=result,
                error=result.message,
            )
    except HTTPException:
        raise
    except Exception as e:
        return RepairResponse(
            vulnerability_id=request.vulnerability_id,
            status="failed",
            error=str(e),
        )
