from __future__ import annotations
from typing import Any, Dict
from pydantic import BaseModel

class Tool:
    name: str
    description: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]

    def _run(self, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError

    def run(self, **kwargs) -> Dict[str, Any]:
        print(f"Running {self.name} with args: {kwargs}", flush=True)
        return self._run(**kwargs)