from fastapi import APIRouter
from .imports import router as imports_router
from .students import router as students_router

router = APIRouter()
router.include_router(imports_router)
router.include_router(students_router)
