from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PetBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    species: str = Field(min_length=1, max_length=80)
    breed: str | None = Field(default=None, max_length=120)
    sex: str | None = Field(default=None, max_length=40)
    date_of_birth: date | None = None
    weight_kg: float | None = Field(default=None, gt=0, le=5000)
    profile_image_url: str | None = Field(default=None, max_length=500)

    @field_validator("date_of_birth")
    @classmethod
    def birth_date_cannot_be_in_future(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return value


class PetCreate(PetBase):
    pass


class PetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    species: str | None = Field(default=None, min_length=1, max_length=80)
    breed: str | None = Field(default=None, max_length=120)
    sex: str | None = Field(default=None, max_length=40)
    date_of_birth: date | None = None
    weight_kg: float | None = Field(default=None, gt=0, le=5000)
    profile_image_url: str | None = Field(default=None, max_length=500)

    @field_validator("date_of_birth")
    @classmethod
    def birth_date_cannot_be_in_future(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return value


class PetResponse(PetBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime

