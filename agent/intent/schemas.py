"""意图 Schema 定义"""

from pydantic import BaseModel
from typing import Any


class Intent(BaseModel):
    action: str
    params: dict[str, Any] = {}
    confidence: float = 0.0
