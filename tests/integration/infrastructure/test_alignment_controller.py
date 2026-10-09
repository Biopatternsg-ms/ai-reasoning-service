import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from src.main import app
from src.infrastructure.container import container
from src.domain.models.alignment_proposal import AlignmentProposal
from src.domain.models.entity import AlignedItem, AlignmentStatus


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    response = client.get("/ai-reasoning/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UP"
    assert "llm_provider" in data


def test_missing_x_user_id_header(client):
    response = client.post("/ai-reasoning/alignments/v1/proposal/test-pipe-1")
    assert response.status_code == 422  # Missing mandatory header


def test_successful_alignment_proposal_flow(client, monkeypatch):
    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = AlignmentProposal(
        pipeline_id="pipe-100",
        objects=[
            AlignedItem(
                current="SST",
                aligned="SST",
                status=AlignmentStatus.DIRECT_MATCH,
                reason="Direct match in PubTator"
            ),
            AlignedItem(
                current="TATA",
                aligned="TBP",
                status=AlignmentStatus.RESOLVED_BY_AI,
                reason="TATA-binding protein [Criterion: canonical_gene_mapping]",
                pubmed_ids=["10523821"]
            ),
            AlignedItem(
                current="AMBIG1",
                aligned="GENE_A",
                status=AlignmentStatus.RESOLVED_BY_DATABASE,
                reason="Selected from BiopatternsG database (HGNC: 1234, UniProt: P99999)",
                pubmed_ids=[]
            )
        ]
    )

    monkeypatch.setattr(container, "get_alignment_use_case", lambda: mock_use_case)

    response = client.post(
        "/ai-reasoning/alignments/v1/proposal/pipe-100",
        headers={"x-user-id": "user-test-777"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["pipelineId"] == "pipe-100"
    assert len(data["objects"]) == 3
    assert data["objects"][0]["current"] == "SST"
    assert data["objects"][0]["status"] == "DIRECT_MATCH"
    assert data["objects"][0]["pubmedIds"] == []
    assert data["objects"][1]["current"] == "TATA"
    assert data["objects"][1]["aligned"] == "TBP"
    assert data["objects"][1]["status"] == "RESOLVED_BY_AI"
    assert data["objects"][1]["pubmedIds"] == ["10523821"]
    assert data["objects"][2]["current"] == "AMBIG1"
    assert data["objects"][2]["aligned"] == "GENE_A"
    assert data["objects"][2]["status"] == "RESOLVED_BY_DATABASE"
    assert data["objects"][2]["pubmedIds"] == []
