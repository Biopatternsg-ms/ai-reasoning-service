import logging
from fastapi import APIRouter, HTTPException, Depends, Header

from src.application.use_cases.alignment_use_case import GenerateAlignmentProposalUseCase
from src.domain.exceptions.exceptions import AlignmentException, EntityValidationException
from src.infrastructure.container import container
from src.infrastructure.delivery.rest.dtos.alignment_dto import AlignmentProposalResponseDTO

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-reasoning/alignments/v1", tags=["Alignments"])


def get_alignment_use_case() -> GenerateAlignmentProposalUseCase:
    """Dependency provider retrieving the use case from the DI container."""
    return container.get_alignment_use_case()


@router.post(
    "/proposal/{pipelineId}",
    response_model=AlignmentProposalResponseDTO,
    summary="Generates a biological alignment proposal for pipeline entities"
)
async def generate_alignment_proposal(
    pipelineId: str,
    x_user_id: str = Header(..., alias="x-user-id", description="Authenticated user ID provided by API Gateway"),
    use_case: GenerateAlignmentProposalUseCase = Depends(get_alignment_use_case)
) -> AlignmentProposalResponseDTO:
    """
    Endpoint generating the biological entity alignment proposal:
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
        domain_proposal = await use_case.execute(
            pipeline_id=pipelineId.strip(),
            user_id=x_user_id.strip()
        )
        return AlignmentProposalResponseDTO.from_domain(domain_proposal)

    except EntityValidationException as e:
        logger.warning(f"Validation error for pipelineId '{pipelineId}': {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except AlignmentException as e:
        logger.error(f"Alignment error for pipelineId '{pipelineId}': {str(e)}")
        raise HTTPException(status_code=502, detail=str(e))

    except Exception as e:
        logger.error(f"Internal error processing proposal for pipelineId '{pipelineId}': {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error generating alignment proposal: {str(e)}"
        )
