import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { speciesFeeRupees } from '../species'
import type { PetSpecies } from '../types'

/** Fee display should come from the backend (the actual source of the charge), not the hardcoded
 * fallback table in species.ts — that table only covers the brief window before this loads. */
export function usePricing() {
  const query = useQuery({
    queryKey: ['pricing'],
    queryFn: () => api.get<Record<string, number>>('/pricing'),
    staleTime: Infinity,
  })

  function feeRupees(species: PetSpecies): number {
    const paise = query.data?.[species]
    return paise !== undefined ? Math.round(paise / 100) : speciesFeeRupees(species)
  }

  return { feeRupees }
}
