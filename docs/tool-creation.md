# Creating a tool

Subclass `jarvis.tools.base.Tool`, define immutable metadata, validate input with a Pydantic model, and implement async `run`. Register the instance in the composition root (or an entry-point loader in a future package). Mark destructive or privileged operations as `requires_confirmation=True`; the manager enforces this before execution.
