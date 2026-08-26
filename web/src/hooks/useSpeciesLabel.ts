import { useLanguage } from '../i18n/LanguageContext'
import { speciesDisplayLabel } from '../species'
import type { PetSpecies } from '../types'

/** Species name for display, following the current language — never use this value for
 * anything sent to the backend (booking still needs the stable English speciesLabel()). */
export function useSpeciesLabel() {
  const { language } = useLanguage()
  return (species: PetSpecies) => speciesDisplayLabel(species, language)
}
