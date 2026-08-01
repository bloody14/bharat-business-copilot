from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class PlaceholderResponse(BaseModel):
    module: str
    status: str
    message: str


@router.get("/{module}", response_model=PlaceholderResponse)
def module_placeholder(module: str) -> PlaceholderResponse:
    """Temporary endpoint boundary; intentionally contains no business logic."""
    return PlaceholderResponse(module=module, status="not_implemented", message="Planned for a future sprint.")
