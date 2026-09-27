import logging
from fastapi import APIRouter, HTTPException, Depends, Header
from src.models.alignment_dto import AlignmentProposalResponse
from src.services.alignment_service import AlignmentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-reasoning/alignments/v1", tags=["Alignments"])


def get_alignment_service() -> AlignmentService:
    return AlignmentService()


@router.post(
    "/proposal/{pipelineId}",
    response_model=AlignmentProposalResponse,
    summary="Generates a biological alignment proposal for pipeline entities"
)
async def generate_alignment_proposal(
    pipelineId: str,
    x_user_id: str = Header(..., alias="x-user-id", description="Authenticated user ID provided by the API Gateway"),
    service: AlignmentService = Depends(get_alignment_service)
) -> AlignmentProposalResponse:
    """
    Endpoint to generate biological entity alignment proposal:
    - Validates the presence of the 'x-user-id' header.
    - Queries pubmed-integration forwarding 'x-user-id'.
    - Uses AI to resolve ambiguous and unaligned entities.
    - Returns the consolidated list for user verification in the UI.
    """
    if not pipelineId or not pipelineId.strip():
        raise HTTPException(status_code=400, detail="Path parameter 'pipelineId' is required.")

    if not x_user_id or not x_user_id.strip():
        raise HTTPException(status_code=400, detail="Header 'x-user-id' is required.")

    try:
        proposal = await service.generate_alignment_proposal(
            pipeline_id=pipelineId.strip(),
            user_id=x_user_id.strip()
        )
        return proposal
    except Exception as e:
        logger.error(f"Error processing proposal for pipelineId '{pipelineId}': {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error generating alignment proposal: {str(e)}"
        )
