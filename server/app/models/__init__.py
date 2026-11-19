# Importing both models here ensures their tables are registered on Base.metadata
# before any call to Base.metadata.create_all(engine).
from app.models.students import Student
from app.models.imports import Import, ImportError

__all__ = ["Student", "Import", "ImportError"]
