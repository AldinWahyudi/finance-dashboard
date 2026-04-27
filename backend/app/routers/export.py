from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import User
from ..services.pdf_export import build_dashboard_pdf
from .dashboard import _build_summary

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/pdf")
def export_pdf(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    summary = _build_summary(db, user)
    pdf_bytes = build_dashboard_pdf(user.email, summary)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="finance-dashboard.pdf"',
        },
    )
