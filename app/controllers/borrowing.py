"""
Borrowing management endpoints.
Covers: SCRUM-28, SCRUM-29, SCRUM-30
"""
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.borrowing import (
    BorrowCreate, BorrowReturn, BorrowingResponse, 
    BorrowingSearchParams, BorrowingStatsResponse, BorrowingSimpleResponse,
    FinePayment, BorrowingUpdate, BorrowingBulkUpdate
)
from app.middleware.auth import get_current_user, require_admin, require_librarian
from app.services.borrowing_service import BorrowingService
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["borrowing"])


@router.post("/borrow", response_model=BorrowingResponse, status_code=status.HTTP_201_CREATED)
async def borrow_book(
    borrow_data: BorrowCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Borrow a book.
    
    Allows authenticated users to borrow a book from the library.
    The user_id in the request can be omitted to use the current user's ID.
    """
    logger.info(f"User {current_user['id']} borrowing book {borrow_data.book_id}")
    
    try:
        # Set user ID from current user if not provided
        if not borrow_data.user_id:
            borrow_data.user_id = current_user["id"]
        
        borrowing = await BorrowingService.borrow_book(borrow_data, db)
        
        if not borrowing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot borrow book. Check availability or user limits."
            )
        
        return borrowing
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to borrow book: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to borrow book: {str(e)}"
        )


@router.post("/return", response_model=BorrowingResponse)
async def return_book(
    return_data: BorrowReturn,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Return a borrowed book.
    
    Allows users to return a borrowed book.
    Fine will be calculated automatically if the book is overdue.
    """
    logger.info(f"User {current_user['id']} returning borrowing {return_data.borrowing_id}")
    
    try:
        success, message, fine_amount = await BorrowingService.return_book(return_data, db)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        # Get updated borrowing record
        borrowing = await BorrowingService.get_borrowing(return_data.borrowing_id, db)
        
        return borrowing
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to return book: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to return book: {str(e)}"
        )


@router.get("/borrowings", response_model=List[BorrowingSimpleResponse])
async def get_borrowings(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    user_id: Optional[int] = Query(None, gt=0, description="Filter by user ID"),
    book_id: Optional[int] = Query(None, gt=0, description="Filter by book ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    overdue_only: bool = Query(False, description="Only show overdue borrowings"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_librarian)
) -> Any:
    """
    Get borrowing records.
    
    Returns a list of borrowing records with filtering options.
    Requires librarian or admin role.
    """
    logger.info(f"User {current_user['id']} getting borrowings (skip={skip}, limit={limit})")
    
    try:
        search_params = BorrowingSearchParams(
            user_id=user_id,
            book_id=book_id,
            status=status,
            overdue_only=overdue_only
        )
        
        borrowings = await BorrowingService.search_borrowings(search_params, skip, limit, db)
        return borrowings
    except Exception as e:
        logger.error(f"Failed to get borrowings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get borrowings: {str(e)}"
        )


@router.get("/borrowings/me", response_model=List[BorrowingSimpleResponse])
async def get_my_borrowings(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Get current user's borrowing history.
    
    Returns the borrowing history for the currently authenticated user.
    """
    logger.info(f"User {current_user['id']} getting their borrowings")
    
    try:
        search_params = BorrowingSearchParams(
            user_id=current_user["id"],
            status=status
        )
        
        borrowings = await BorrowingService.search_borrowings(search_params, skip, limit, db)
        return borrowings
    except Exception as e:
        logger.error(f"Failed to get user borrowings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get borrowings: {str(e)}"
        )


@router.get("/borrowings/{borrowing_id}", response_model=BorrowingResponse)
async def get_borrowing(
    borrowing_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Get a specific borrowing record.
    
    Returns detailed information about a specific borrowing record.
    Users can only see their own borrowings unless they are admin/librarian.
    """
    logger.info(f"User {current_user['id']} getting borrowing: {borrowing_id}")
    
    try:
        borrowing = await BorrowingService.get_borrowing(borrowing_id, db)
        
        if not borrowing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Borrowing not found: {borrowing_id}"
            )
        
        # Check permission (user can only see their own borrowings unless admin/librarian)
        if (current_user["id"] != borrowing.user_id and 
            current_user.get("role") not in ["admin", "librarian"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this borrowing"
            )
        
        return borrowing
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get borrowing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get borrowing: {str(e)}"
        )


@router.get("/borrowings/stats", response_model=BorrowingStatsResponse)
async def get_borrowing_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_librarian)
) -> Any:
    """
    Get borrowing statistics.
    
    Returns statistics about borrowings in the library.
    Requires librarian or admin role.
    """
    logger.info(f"User {current_user['id']} getting borrowing stats")
    
    try:
        stats = await BorrowingService.get_borrowing_stats(db)
        return stats
    except Exception as e:
        logger.error(f"Failed to get borrowing stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get borrowing stats: {str(e)}"
        )


@router.get("/borrowings/overdue", response_model=List[BorrowingSimpleResponse])
async def get_overdue_borrowings(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_librarian)
) -> Any:
    """
    Get overdue borrowings.
    
    Returns a list of overdue borrowing records.
    Requires librarian or admin role.
    """
    logger.info(f"User {current_user['id']} getting overdue borrowings (skip={skip}, limit={limit})")
    
    try:
        search_params = BorrowingSearchParams(overdue_only=True)
        borrowings = await BorrowingService.search_borrowings(search_params, skip, limit, db)
        return borrowings
    except Exception as e:
        logger.error(f"Failed to get overdue borrowings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get overdue borrowings: {str(e)}"
        )


@router.post("/borrowings/{borrowing_id}/pay-fine", response_model=dict)
async def pay_fine(
    borrowing_id: int,
    payment_data: FinePayment,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Pay fine for a borrowing.
    
    Allows users to pay fines for overdue books.
    Users can only pay fines for their own borrowings unless they are admin/librarian.
    """
    logger.info(f"User {current_user['id']} paying fine for borrowing {borrowing_id}")
    
    try:
        # Get borrowing to check ownership
        borrowing = await BorrowingService.get_borrowing(borrowing_id, db)
        
        if not borrowing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Borrowing not found: {borrowing_id}"
            )
        
        # Check permission (user can only pay their own fines unless admin/librarian)
        if (current_user["id"] != borrowing.user_id and 
            current_user.get("role") not in ["admin", "librarian"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to pay this fine"
            )
        
        success, message = await BorrowingService.pay_fine(borrowing_id, payment_data.amount, db)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        return {
            "success": True,
            "message": message,
            "borrowing_id": borrowing_id,
            "amount_paid": payment_data.amount
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pay fine: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pay fine: {str(e)}"
        )


@router.post("/borrowings/update-overdue", response_model=dict)
async def update_overdue_borrowings(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
) -> Any:
    """
    Update status of overdue borrowings.
    
    Updates the status of all overdue borrowings to OVERDUE.
    Requires admin role.
    """
    logger.info(f"Admin {current_user['id']} updating overdue borrowings")
    
    try:
        updated_count = await BorrowingService.update_overdue_status(db)
        
        return {
            "updated_count": updated_count,
            "message": f"Updated {updated_count} borrowings to OVERDUE status"
        }
    except Exception as e:
        logger.error(f"Failed to update overdue borrowings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update overdue borrowings: {str(e)}"
        )


@router.put("/borrowings/{borrowing_id}", response_model=BorrowingResponse)
async def update_borrowing(
    borrowing_id: int,
    update_data: BorrowingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_librarian)
) -> Any:
    """
    Update a borrowing record.
    
    Updates a borrowing record (e.g., extend due date, update status).
    Requires librarian or admin role.
    """
    logger.info(f"User {current_user['id']} updating borrowing: {borrowing_id}")
    
    try:
        borrowing = await BorrowingService.get_borrowing(borrowing_id, db)
        
        if not borrowing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Borrowing not found: {borrowing_id}"
            )
        
        # Update fields
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(borrowing, field, value)
        
        borrowing.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(borrowing)
        
        return borrowing
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update borrowing: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update borrowing: {str(e)}"
        )


@router.put("/borrowings/bulk", response_model=dict)
async def bulk_update_borrowings(
    bulk_data: BorrowingBulkUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
) -> Any:
    """
    Update multiple borrowing records at once.
    
    Updates multiple borrowing records in a single request.
    Requires admin role.
    """
    logger.info(f"Admin {current_user['id']} bulk updating {len(bulk_data.borrowing_ids)} borrowings")
    
    try:
        updated_count = 0
        errors = []
        
        for borrowing_id in bulk_data.borrowing_ids:
            try:
                borrowing = await BorrowingService.get_borrowing(borrowing_id, db)
                if borrowing:
                    update_dict = bulk_data.update_data.dict(exclude_unset=True)
                    for field, value in update_dict.items():
                        setattr(borrowing, field, value)
                    borrowing.updated_at = datetime.utcnow()
                    updated_count += 1
            except Exception as e:
                errors.append(f"Borrowing {borrowing_id}: {str(e)}")
        
        if updated_count > 0:
            await db.commit()
        
        return {
            "updated_count": updated_count,
            "total_requested": len(bulk_data.borrowing_ids),
            "errors": errors,
            "message": f"Updated {updated_count} borrowings successfully"
        }
    except Exception as e:
        logger.error(f"Failed to bulk update borrowings: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk update borrowings: {str(e)}"
        )