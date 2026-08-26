from fastapi import APIRouter

from app.core.pricing import SPECIES_FEE_PAISE

router = APIRouter()


@router.get("/pricing", response_model=dict[str, int])
def read_species_pricing() -> dict[str, int]:
    """Consultation fee in paise per species — the source of truth the frontend displays from."""
    return {species.value: fee_paise for species, fee_paise in SPECIES_FEE_PAISE.items()}
