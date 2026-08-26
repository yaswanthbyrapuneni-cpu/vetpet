import type { Language } from './i18n/LanguageContext'
import type { PetSpecies } from './types'

export const SPECIES_OPTIONS: { value: PetSpecies; label: string; feeRupees: number; emoji: string }[] = [
  { value: 'dog', label: 'Dog', feeRupees: 200, emoji: '🐕' },
  { value: 'cat', label: 'Cat', feeRupees: 200, emoji: '🐈' },
  { value: 'cow', label: 'Cow', feeRupees: 200, emoji: '🐄' },
  { value: 'buffalo', label: 'Buffalo', feeRupees: 200, emoji: '🐃' },
  { value: 'farm_hen', label: 'Farm hen', feeRupees: 200, emoji: '🐔' },
  { value: 'sheep', label: 'Sheep', feeRupees: 50, emoji: '🐑' },
  { value: 'goat', label: 'Goat', feeRupees: 50, emoji: '🐐' },
  { value: 'other', label: 'Other', feeRupees: 50, emoji: '🐾' },
  { value: 'country_hen', label: 'Country hen', feeRupees: 25, emoji: '🐓' },
]

// Species that share a fee are shown as one card with multiple tap targets, instead of
// repeating the same price across several separate cards.
export const SPECIES_GROUPS: PetSpecies[][] = [
  ['dog', 'cat'],
  ['cow', 'buffalo'],
  ['farm_hen'],
  ['sheep', 'goat'],
  ['other'],
  ['country_hen'],
]

const SPECIES_BY_VALUE = new Map(SPECIES_OPTIONS.map((option) => [option.value, option]))

// This is the *canonical* (always-English) label — it's what gets sent to the backend as
// the pet's name on booking, so it must stay stable regardless of display language, or the
// same animal booked in English vs Telugu would be recorded as two different pets.
export function speciesLabel(species: PetSpecies): string {
  return SPECIES_BY_VALUE.get(species)?.label ?? species
}

// Telugu display names — kept separate from speciesLabel() above, which must never change
// with language. "Dog" is intentionally left in English here per product decision.
const SPECIES_LABELS_TE: Record<PetSpecies, string> = {
  dog: 'Dog',
  cat: 'పిల్లి',
  cow: 'ఆవు',
  buffalo: 'గేదె',
  farm_hen: 'ఫారం కోడి',
  sheep: 'గొర్రె',
  goat: 'మేక',
  other: 'ఇతర',
  country_hen: 'నాటు కోడి',
}

/** The label to actually display for the given language — use this everywhere a species
 * name is shown to a user. Only speciesLabel() above should feed the booking API. */
export function speciesDisplayLabel(species: PetSpecies, language: Language): string {
  return language === 'te' ? SPECIES_LABELS_TE[species] : speciesLabel(species)
}

export function speciesFeeRupees(species: PetSpecies): number {
  return SPECIES_BY_VALUE.get(species)?.feeRupees ?? 50
}

export function speciesEmoji(species: PetSpecies): string {
  return SPECIES_BY_VALUE.get(species)?.emoji ?? '🐾'
}
