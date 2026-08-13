import { Edit3, MoreVertical, PawPrint, Plus, Scale, Trash2, X } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { api, ApiError } from '../api/client'
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/Feedback'
import type { Pet } from '../types'

type PetDraft = Pick<Pet, 'name' | 'species' | 'breed' | 'sex' | 'date_of_birth' | 'weight_kg'>
const emptyDraft: PetDraft = { name: '', species: '', breed: null, sex: null, date_of_birth: null, weight_kg: null }

export function PetsPage() {
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: ['pets'], queryFn: () => api.get<Pet[]>('/pets') })
  const [editing, setEditing] = useState<Pet | null | 'new'>(null)
  const archive = useMutation({
    mutationFn: (id: string) => api.delete(`/pets/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['pets'] }),
  })

  async function archivePet(pet: Pet) {
    if (window.confirm(`Archive ${pet.name}? Medical history will be preserved.`)) await archive.mutateAsync(pet.id)
  }

  return <div className="page-content">
    <header className="page-heading split"><div><span className="eyebrow">Pet profiles</span><h1>My pets</h1><p>Keep every pet's essential details organized.</p></div><button className="button primary" onClick={() => setEditing('new')}><Plus size={18} />Add pet</button></header>
    {query.isLoading ? <LoadingBlock /> : query.isError ? <ErrorBlock message={query.error instanceof ApiError ? query.error.message : 'Unable to load pets.'} retry={() => void query.refetch()} /> : query.data?.length === 0 ? <div className="empty-card"><EmptyBlock title="Add your first pet" text="Create a profile to begin managing appointments and medical history." /><button className="button primary" onClick={() => setEditing('new')}><Plus size={18} />Add pet</button></div> : <div className="pet-grid">{query.data?.map((pet) => <article className="pet-card" key={pet.id}><div className="pet-card-top"><span className="pet-avatar"><PawPrint /></span><div className="menu-wrap"><button className="icon-button menu-trigger" aria-label={`Actions for ${pet.name}`}><MoreVertical /></button><div className="card-menu"><button onClick={() => setEditing(pet)}><Edit3 />Edit</button><button className="danger" onClick={() => void archivePet(pet)}><Trash2 />Archive</button></div></div></div><h2>{pet.name}</h2><p className="pet-kind">{[pet.species, pet.breed].filter(Boolean).join(' · ')}</p><div className="pet-meta">{pet.weight_kg && <span><Scale />{pet.weight_kg} kg</span>}{pet.sex && <span>{pet.sex}</span>}{pet.date_of_birth && <span>Born {new Date(pet.date_of_birth).toLocaleDateString()}</span>}</div><button className="text-button" onClick={() => setEditing(pet)}>Edit profile</button></article>)}</div>}
    {editing && <PetDialog pet={editing === 'new' ? null : editing} onClose={() => setEditing(null)} />}
  </div>
}

function PetDialog({ pet, onClose }: { pet: Pet | null; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState<PetDraft>(pet ? { name: pet.name, species: pet.species, breed: pet.breed, sex: pet.sex, date_of_birth: pet.date_of_birth, weight_kg: pet.weight_kg } : emptyDraft)
  const [error, setError] = useState<string | null>(null)
  const save = useMutation({
    mutationFn: () => pet ? api.patch(`/pets/${pet.id}`, draft) : api.post('/pets', draft),
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ['pets'] }); onClose() },
    onError: (caught) => setError(caught instanceof Error ? caught.message : 'Unable to save pet.'),
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    if (draft.weight_kg !== null && draft.weight_kg <= 0) { setError('Weight must be greater than zero.'); return }
    save.mutate()
  }

  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><div className="modal" role="dialog" aria-modal="true" aria-labelledby="pet-dialog-title"><header><div><span className="eyebrow">Pet profile</span><h2 id="pet-dialog-title">{pet ? `Edit ${pet.name}` : 'Add a new pet'}</h2></div><button className="icon-button" onClick={onClose}><X /></button></header><form onSubmit={submit}><div className="form-grid"><label>Pet name<input value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} required maxLength={120} autoFocus /></label><label>Species<input value={draft.species} onChange={(event) => setDraft({ ...draft, species: event.target.value })} required maxLength={80} placeholder="Dog, cat, bird…" /></label><label>Breed <small>Optional</small><input value={draft.breed ?? ''} onChange={(event) => setDraft({ ...draft, breed: event.target.value || null })} /></label><label>Sex <small>Optional</small><select value={draft.sex ?? ''} onChange={(event) => setDraft({ ...draft, sex: event.target.value || null })}><option value="">Select</option><option value="male">Male</option><option value="female">Female</option><option value="unknown">Unknown</option></select></label><label>Date of birth <small>Optional</small><input type="date" max={new Date().toISOString().slice(0, 10)} value={draft.date_of_birth ?? ''} onChange={(event) => setDraft({ ...draft, date_of_birth: event.target.value || null })} /></label><label>Weight (kg) <small>Optional</small><input type="number" min="0.01" step="0.01" value={draft.weight_kg ?? ''} onChange={(event) => setDraft({ ...draft, weight_kg: event.target.value ? Number(event.target.value) : null })} /></label></div>{error && <div className="inline-error">{error}</div>}<footer><button type="button" className="button secondary" onClick={onClose}>Cancel</button><button className="button primary" disabled={save.isPending}>{save.isPending ? 'Saving…' : 'Save pet'}</button></footer></form></div></div>
}

