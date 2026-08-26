export type UserRole = 'owner' | 'doctor' | 'admin'

export interface User {
  id: string
  mobile_number: string
  full_name: string
  role: UserRole
  is_active: boolean
}

export type PetSpecies = 'dog' | 'cat' | 'cow' | 'buffalo' | 'sheep' | 'goat' | 'country_hen' | 'farm_hen' | 'other'

export interface Pet {
  id: string
  owner_id: string
  name: string
  species: PetSpecies
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
  is_online: boolean
}

export interface Appointment {
  id: string
  pet_id: string
  doctor_id: string
  species: PetSpecies
  owner_name: string
  owner_mobile_number: string
  scheduled_start: string
  reason: string
  consultation_type: 'video' | 'audio'
  status: 'requested' | 'confirmed' | 'rejected' | 'cancelled' | 'completed' | 'no_show'
  payment_status: 'pending' | 'paid' | 'failed'
  payment_amount_paise: number
  paid_at: string | null
  razorpay_payment_id: string | null
  created_at: string
  updated_at: string
}

export interface AppointmentAttachment {
  id: string
  appointment_id: string
  uploaded_by_user_id: string
  kind: 'photo' | 'video' | 'voice'
  original_filename: string
  content_type: string
  size_bytes: number
  created_at: string
}

export interface AppointmentMessage {
  id: string
  appointment_id: string
  sender_user_id: string
  body: string
  created_at: string
}

export interface AppointmentRating {
  id: string
  appointment_id: string
  rated_by_user_id: string
  stars: number
  tags: string[]
  comment: string | null
  created_at: string
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

export interface ThreadPreview {
  kind: 'message' | 'photo' | 'video' | 'voice'
  text: string | null
  created_at: string
  sender_user_id: string
}

export interface AppointmentThreadSummary {
  appointment_id: string
  pet_name: string
  species: PetSpecies
  owner_name: string
  doctor_name: string
  status: Appointment['status']
  payment_status: Appointment['payment_status']
  consultation_type: Appointment['consultation_type']
  last_activity_at: string
  preview: ThreadPreview | null
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
