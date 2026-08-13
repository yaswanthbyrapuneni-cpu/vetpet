import { Award, Building2, Search, Stethoscope } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { api, ApiError } from '../api/client'
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/Feedback'
import type { Doctor } from '../types'

export function DoctorsPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [search, setSearch] = useState('')
  const query = useQuery({ queryKey: ['doctors'], queryFn: () => api.get<Doctor[]>('/doctors') })
  const doctors = useMemo(() => (query.data ?? []).filter((doctor) => `${doctor.user.full_name} ${doctor.specialization ?? ''} ${doctor.hospital_name ?? ''}`.toLowerCase().includes(search.toLowerCase())), [query.data, search])
  return <div className="page-content">
    <header className="page-heading"><div><span className="eyebrow">Trusted professionals</span><h1>Verified veterinarians</h1><p>Browse veterinary professionals reviewed by VetPet Connect.</p></div></header>
    <div className="toolbar"><div className="search-box"><Search /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by name, specialty, or hospital" /></div></div>
    {query.isLoading ? <LoadingBlock /> : query.isError ? <ErrorBlock message={query.error instanceof ApiError ? query.error.message : 'Unable to load veterinarians.'} retry={() => void query.refetch()} /> : doctors.length === 0 ? <EmptyBlock title="No veterinarians found" text={search ? 'Try a different search.' : 'Verified doctors will appear here.'} /> : <div className="doctor-grid">{doctors.map((doctor) => <article className={`doctor-card ${user?.role === 'owner' ? 'clickable' : ''}`} key={doctor.id} onClick={user?.role === 'owner' ? () => navigate(`/app/doctors/${doctor.id}`) : undefined} onKeyDown={user?.role === 'owner' ? (event) => { if (event.key === 'Enter' || event.key === ' ') navigate(`/app/doctors/${doctor.id}`) } : undefined} role={user?.role === 'owner' ? 'button' : undefined} tabIndex={user?.role === 'owner' ? 0 : undefined}><div className="doctor-avatar"><Stethoscope /></div><div><span className="verified-badge"><Award size={14} />Verified</span><h2>{doctor.user.full_name}</h2><p className="doctor-specialty">{doctor.specialization || 'General veterinary medicine'}</p><dl><div><dt>Qualification</dt><dd>{doctor.qualification}</dd></div><div><dt>Experience</dt><dd>{doctor.experience_years} years</dd></div>{doctor.hospital_name && <div><dt><Building2 size={14} />Hospital</dt><dd>{doctor.hospital_name}</dd></div>}</dl>{user?.role === 'owner' && <span className="book-hint">View times &amp; book</span>}</div></article>)}</div>}
  </div>
}
