from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.scanner.engine import ScannerEngine
from app.scanner.schemas import ScanRequest, ScanResult

router = APIRouter(prefix="/scanner", tags=["Scanner"])

@router.post("/run", response_model=list[ScanResult])
def run_scan(
    request: ScanRequest,
    db: Session = Depends(get_db),
):
    engine = ScannerEngine()

    results = engine.run(request)

    return results