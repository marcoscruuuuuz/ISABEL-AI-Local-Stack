"""ISABEL Agent Fleet Model - up to 100 local 2B agents per tenant."""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid

class AgentStatus(str, Enum):
    PENDING = "pending"
    INSTALLING = "installing"
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    DISABLED = "disabled"

class AgentCapability(str, Enum):
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    SYSTEM_QUERY = "system_query"
    SHELL_SAFE = "shell_safe"
    DATABASE_LOCAL = "database_local"

class FleetAgentCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=64)
    display_name: str
    description: Optional[str] = None
    capabilities: List[AgentCapability] = [AgentCapability.FILE_READ, AgentCapability.SYSTEM_QUERY]
    allow_paths: List[str] = Field(default_factory=lambda: [r"%USERPROFILE%\Documents", r"C:\Projetos", r"C:\Sistemas"])
    deny_paths: List[str] = Field(default_factory=lambda: [r"C:\Windows", r"C:\Program Files"])
    local_systems: List[Dict[str, str]] = Field(default_factory=list)
    auto_start: bool = True
    offline_capable: bool = True

class FleetAgent(BaseModel):
    id: str = Field(default_factory=lambda: f"agt_{uuid.uuid4().hex[:12]}")
    tenant_id: str
    name: str
    display_name: str
    description: Optional[str] = None
    status: AgentStatus = AgentStatus.PENDING
    machine_id: Optional[str] = None
    hostname: Optional[str] = None
    version: str = "1.0.2"
    model_local: str = "Qwen2.5-1.5B-Instruct.Q4_K_M"
    capabilities: List[AgentCapability] = []
    allow_paths: List[str] = []
    deny_paths: List[str] = []
    local_systems: List[Dict[str, str]] = []
    auto_start: bool = True
    offline_capable: bool = True
    agent_token: str = Field(default_factory=lambda: uuid.uuid4().hex)
    last_seen: Optional[datetime] = None
    tokens_used: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    install_key: str = Field(default_factory=lambda: uuid.uuid4().hex[:16].upper())

class FleetAgentUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[AgentStatus] = None
    capabilities: Optional[List[AgentCapability]] = None
    allow_paths: Optional[List[str]] = None
    local_systems: Optional[List[Dict[str, str]]] = None

class AgentQueryRequest(BaseModel):
    agent_name: str
    question: str
    context: Optional[Dict[str, Any]] = None
    timeout_seconds: int = 60

class AgentQueryResponse(BaseModel):
    agent_id: str
    agent_name: str
    question: str
    answer: str
    source: str = "local_2b"
    offline: bool = False
    latency_ms: int = 0
    evidence: Optional[List[Dict[str, Any]]] = None

class TenantTokenUsage(BaseModel):
    tenant_id: str
    period: str
    tokens_used: int
    tokens_quota: int
    cost_brl: float
    by_agent: Dict[str, int] = Field(default_factory=dict)
    by_feature: Dict[str, int] = Field(default_factory=dict)
