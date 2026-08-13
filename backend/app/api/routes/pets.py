from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select

from app.api.dependencies import DbSession, require_roles
from app.models.domain import Pet, User, UserRole, utc_now
from app.schemas.pet import PetCreate, PetResponse, PetUpdate

router = APIRouter(prefix="/pets")
OwnerUser = Annotated[User, Depends(require_roles(UserRole.OWNER))]


def get_owned_pet(pet_id: str, owner: User, db: DbSession) -> Pet:
    pet = db.scalar(
        select(Pet).where(
            Pet.id == pet_id,
            Pet.owner_id == owner.id,
            Pet.is_archived.is_(False),
        )
    )
    if pet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")
    return pet


@router.post("", response_model=PetResponse, status_code=status.HTTP_201_CREATED)
def create_pet(payload: PetCreate, owner: OwnerUser, db: DbSession) -> Pet:
    pet = Pet(owner_id=owner.id, **payload.model_dump())
    db.add(pet)
    db.commit()
    db.refresh(pet)
    return pet


@router.get("", response_model=list[PetResponse])
def list_pets(
    owner: OwnerUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Pet]:
    statement = (
        select(Pet)
        .where(Pet.owner_id == owner.id, Pet.is_archived.is_(False))
        .order_by(Pet.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement))


@router.get("/{pet_id}", response_model=PetResponse)
def read_pet(pet_id: str, owner: OwnerUser, db: DbSession) -> Pet:
    return get_owned_pet(pet_id, owner, db)


@router.patch("/{pet_id}", response_model=PetResponse)
def update_pet(pet_id: str, payload: PetUpdate, owner: OwnerUser, db: DbSession) -> Pet:
    pet = get_owned_pet(pet_id, owner, db)
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"] is None:
        raise HTTPException(status_code=422, detail="Pet name cannot be null")
    if "species" in updates and updates["species"] is None:
        raise HTTPException(status_code=422, detail="Pet species cannot be null")
    for field, value in updates.items():
        setattr(pet, field, value)
    db.commit()
    db.refresh(pet)
    return pet


@router.delete("/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_pet(pet_id: str, owner: OwnerUser, db: DbSession) -> Response:
    pet = get_owned_pet(pet_id, owner, db)
    pet.is_archived = True
    pet.archived_at = utc_now()
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

