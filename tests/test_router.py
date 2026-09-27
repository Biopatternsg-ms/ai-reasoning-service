import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock
from src.main import app
from src.routers.alignment_router import get_alignment_service
from src.models.alignment_dto import AlignmentProposalResponse, AlignedItem


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ai-reasoning/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "UP"
        assert data["service"] == "ai-reasoning-service"


@pytest.mark.asyncio
async def test_alignment_proposal_endpoint():
    # Mock AlignmentService
    mock_service = AsyncMock()
    mock_service.generate_alignment_proposal.return_value = AlignmentProposalResponse(
        pipelineId="pipe-test-99",
        objects=[
            AlignedItem(
                current="SST",
                aligned="SST",
                status="DIRECT_MATCH",
                reason="Direct match"
            ),
            AlignedItem(
                current="TATA",
                aligned="TBP",
                status="RESOLVED_BY_AI",
                reason="TATA-binding protein"
            )
        ]
    )

    app.dependency_overrides[get_alignment_service] = lambda: mock_service

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Successful request with x-user-id header
            response = await client.post(
                "/ai-reasoning/alignments/v1/proposal/pipe-test-99",
                headers={"x-user-id": "user-test-uuid-123"}
            )
            assert response.status_code == 200

            data = response.json()
            assert data["pipelineId"] == "pipe-test-99"
            assert len(data["objects"]) == 2
            assert data["objects"][0]["current"] == "SST"
            assert data["objects"][0]["aligned"] == "SST"
            assert data["objects"][0]["status"] == "DIRECT_MATCH"
            assert data["objects"][1]["current"] == "TATA"
            assert data["objects"][1]["aligned"] == "TBP"
            assert data["objects"][1]["status"] == "RESOLVED_BY_AI"

            # 2. Rejected request when x-user-id header is missing
            response_missing = await client.post("/ai-reasoning/alignments/v1/proposal/pipe-test-99")
            assert response_missing.status_code == 422  # FastAPI validation error for missing header
    finally:
        app.dependency_overrides.clear()
