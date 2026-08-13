export type UserRole = 'owner' | 'doctor' | 'admin'

export interface User {
  id: string
  email: string
  full_name: string
  phone: string | null
  role: UserRole
  is_active: boolean
  is_email_verified: boolean
}

export interface Pet {
  id: string
  owner_id: string
  name: string
  species: string
  breed: string | null
  sex: string | null
  date_of_birth: string | null
  weight_kg: number | null
  profile_image_url: string | null
  created_at: string
  updated_at: string
}

export interface Doctor {
  id: string
  user: User
  license_number: string
  qualification: string
  specialization: string | null
  experience_years: number
  hospital_name: string | null
  bio: string | null
  verification_status: 'pending' | 'verified' | 'rejected'
  verification_note: string | null
}

export interface Availability {
  id: string
  doctor_id: string
  starts_at: string
  ends_at: string
  is_booked: boolean
}

export interface Appointment {
  id: string
  pet_id: string
  doctor_id: string
  availability_id: string
  scheduled_start: string
  scheduled_end: string
  reason: string
  consultation_type: 'video' | 'audio'
  status: 'requested' | 'confirmed' | 'rejected' | 'cancelled' | 'completed'
}

export interface CallRecording {
  id: string
  appointment_id: string
  recorded_by_user_id: string
  original_filename: string
  content_type: string
  size_bytes: number
  sha256: string
  duration_seconds: number | null
  consent_confirmed_at: string
  created_at: string
}

export interface Notification {
  id: string
  notification_type: 'appointment' | 'prescription' | 'reminder' | 'system'
  title: string
  message: string
  data: Record<string, unknown>
  created_at: string
  read_at: string | null
}
