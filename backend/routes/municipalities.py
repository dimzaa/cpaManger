"""
Municipality routes for CRUD operations.

Endpoints for:
- List all municipalities
- Get specific municipality
- Create new municipality
- Update municipality
- Delete municipality
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from typing import Optional

from backend.database import get_db
from backend.models import Municipality, User
from backend.schemas import MunicipalityCreate, MunicipalityUpdate, MunicipalityList, Municipality as MunicipalitySchema
from backend.utils.auth_guards import require_login, require_admin
from backend.utils.serializers import bytes_to_string

router = APIRouter(
    prefix="/api/municipalities",
    tags=["municipalities"],
)


@router.get("/", response_model=List[MunicipalityList])
def list_municipalities(
    current_user: User = Depends(require_login),
    include_test: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get all municipalities.
    
    **Requires authentication.**
    
        Args:
            include_test: If False (default), excludes test/demo municipalities.
                         If True, shows all including test data (admin only).
    
    Returns:
        List of municipalities with their details
    """
    try:
        print(f"\n📍 MUNICIPALITIES LIST DEBUG:")
        # Filter out test data unless explicitly requested by an admin
        q = db.query(Municipality)
        if not include_test or current_user.role != "admin":
            q = q.filter(Municipality.is_test == False)
        municipalities = q.all()
        print(f"   Total municipalities: {len(municipalities)}")
        
        # Convert code to string and return
        result = []
        for mun in municipalities:
            print(f"   - {mun.name} (ID: {mun.id}, Code: {mun.code})")
            # Create dict with code as string, cleaning all bytes fields
            mun_dict = {
                "id": mun.id,
                "code": bytes_to_string(mun.code),  # Convert bytes to string
                "name": bytes_to_string(mun.name),  # Convert bytes to string
                "login_email": mun.login_email,
                "created_at": mun.created_at,
            }
            result.append(mun_dict)
        
        print(f"   ✅ Returning {len(result)} municipalities")
        return result
    except Exception as e:
        print(f"   ❌ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching municipalities: {str(e)}"
        )


@router.get("/{municipality_id}", response_model=MunicipalitySchema)
def get_municipality(
    municipality_id: int,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    """
    Get a specific municipality by ID.
    
    **Requires authentication.**
    
    Args:
        municipality_id: ID of the municipality
        
    Returns:
        Municipality details
        
    Raises:
        HTTPException 404: If municipality not found
    """
    municipality = db.query(Municipality).filter(
        Municipality.id == municipality_id
    ).first()
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Municipality {municipality_id} not found"
        )
    
    return municipality


@router.get("/code/{code}", response_model=MunicipalitySchema)
def get_municipality_by_code(
    code: str,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    """
    Get a municipality by its Ministry code.
    
    **Requires authentication.**
    
    Args:
        code: Ministry code of the municipality (e.g., "3000")
        
    Returns:
        Municipality details
        
    Raises:
        HTTPException 404: If municipality not found
    """
    municipality = db.query(Municipality).filter(
        Municipality.code == code
    ).first()
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Municipality with code {code} not found"
        )
    
    return municipality


@router.post("/", response_model=MunicipalitySchema, status_code=status.HTTP_201_CREATED)
def create_municipality(
    municipality: MunicipalityCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new municipality.
    
    **Requires admin (CPA) access.**
    
    Args:
        municipality: Municipality data to create
        
    Returns:
        Created municipality details
        
    Raises:
        HTTPException 400: If code already exists
    """
    # Check if code already exists
    existing = db.query(Municipality).filter(
        Municipality.code == municipality.code
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Municipality with code {municipality.code} already exists"
        )
    
    # Create new municipality
    new_municipality = Municipality(**municipality.dict())
    db.add(new_municipality)
    db.commit()
    db.refresh(new_municipality)
    
    return new_municipality


@router.put("/{municipality_id}", response_model=MunicipalitySchema)
def update_municipality(
    municipality_id: int,
    update_data: MunicipalityUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update an existing municipality.
    
    **Requires admin (CPA) access.**
    
    Args:
        municipality_id: ID of municipality to update
        update_data: Fields to update
        
    Returns:
        Updated municipality details
        
    Raises:
        HTTPException 404: If municipality not found
    """
    municipality = db.query(Municipality).filter(
        Municipality.id == municipality_id
    ).first()
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Municipality {municipality_id} not found"
        )
    
    # Check if new code conflicts with existing
    if update_data.code:
        existing = db.query(Municipality).filter(
            Municipality.code == update_data.code,
            Municipality.id != municipality_id,
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Code {update_data.code} already exists for another municipality"
            )
    
    # Update fields
    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(municipality, field, value)
    
    db.commit()
    db.refresh(municipality)
    
    return municipality


@router.delete("/{municipality_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_municipality(
    municipality_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a municipality.
    
    **Requires admin (CPA) access.**
    
    ⚠️ WARNING: This also deletes all associated monthly runs and budget lines.
    
    Args:
        municipality_id: ID of municipality to delete
        
    Raises:
        HTTPException 404: If municipality not found
    """
    municipality = db.query(Municipality).filter(
        Municipality.id == municipality_id
    ).first()
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Municipality {municipality_id} not found"
        )
    
    db.delete(municipality)
    db.commit()
    
    return None
