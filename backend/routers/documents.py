from fastapi import APIRouter, Depends, HTTPException
from routers.auth_helper import get_current_user
from models.database import get_user_cases, delete_dispute_case

router = APIRouter()

@router.get("/dashboard/cases")
async def fetch_cases(user_id: str = Depends(get_current_user)):
    """
    Retrieves all past medical claim dispute analysis cases for the authenticated user.
    """
    try:
        cases = await get_user_cases(user_id)
        return cases
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"An error occurred while fetching case history: {str(e)}"
        )

@router.delete("/dashboard/cases/{case_id}")
async def delete_case(case_id: str, user_id: str = Depends(get_current_user)):
    """
    Deletes a specific dispute case for the authenticated user.
    """
    try:
        success = await delete_dispute_case(case_id, user_id)
        if not success:
            raise HTTPException(
                status_code=404, 
                detail="Case not found or unauthorized to delete."
            )
        return {"message": "Case successfully deleted."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while deleting the case: {str(e)}"
        )
