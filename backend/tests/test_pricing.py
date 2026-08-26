from fastapi.testclient import TestClient

from app.core.pricing import SPECIES_FEE_PAISE


def test_pricing_endpoint_matches_backend_fee_table(client: TestClient) -> None:
    response = client.get("/api/v1/pricing")
    assert response.status_code == 200
    body = response.json()
    for species, fee_paise in SPECIES_FEE_PAISE.items():
        assert body[species.value] == fee_paise
