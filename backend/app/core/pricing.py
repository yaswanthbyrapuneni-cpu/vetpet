from app.models.domain import PetSpecies

SPECIES_FEE_PAISE: dict[PetSpecies, int] = {
    PetSpecies.DOG: 20000,
    PetSpecies.CAT: 20000,
    PetSpecies.COW: 20000,
    PetSpecies.BUFFALO: 20000,
    PetSpecies.FARM_HEN: 20000,
    PetSpecies.SHEEP: 5000,
    PetSpecies.GOAT: 5000,
    PetSpecies.OTHER: 5000,
    PetSpecies.COUNTRY_HEN: 2500,
}
