import { describe, expect, it } from 'vitest'
import type { Doctor, Pet } from './types'

describe('VetPet domain contracts', () => {
  it('supports structured pet profiles', () => {
    const pet: Pet = {
      id: 'pet-1', owner_id: 'owner-1', name: 'Milo', species: 'Dog', breed: 'Indie', sex: 'male',
      date_of_birth: '2022-04-10', weight_kg: 18.4, profile_image_url: null,
      created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
    }
    expect(pet.weight_kg).toBe(18.4)
  })

  it('represents verified doctors from the API', () => {
    const doctor = {
      id: 'doctor-1', qualification: 'BVSc', specialization: 'Small animals', experience_years: 5,
      hospital_name: null, bio: null, license_number: 'VET-1', verification_status: 'verified', verification_note: null,
      user: { id: 'user-1', email: 'vet@example.com', full_name: 'Dr Vet', phone: null, role: 'doctor', is_active: true, is_email_verified: true },
    } satisfies Doctor
    expect(doctor.verification_status).toBe('verified')
  })
})
