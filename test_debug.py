#!/usr/bin/env python3
"""Debug script to test pydantic model."""

from pydantic import BaseModel
from adk_agui_middleware.tools.json_encoder import DataclassesEncoder

class TestModel(BaseModel):
    name: str = "test"
    value: int = 42

model = TestModel()
print("Model created:", model)
print("isinstance BaseModel:", isinstance(model, BaseModel))
print("model_dump:", model.model_dump())

encoder = DataclassesEncoder()
try:
    result = encoder.default(model)
    print("Encoder result:", result)
except Exception as e:
    print("Encoder error:", e)