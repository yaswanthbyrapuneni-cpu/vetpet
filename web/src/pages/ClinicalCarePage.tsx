import { ArrowLeft, CalendarClock, MessageCircle, Pencil, Pill, Plus, Save, Stethoscope, Trash2 } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { LoadingBlock } from '../components/Feedback'
import { useSpeciesLabel } from '../hooks/useSpeciesLabel'
import { useLanguage } from '../i18n/LanguageContext'
import type { Appointment } from '../types'

interface Consultation { id: string; diagnosis: string | null; doctor_notes?: string | null; approved_summary: string | null; follow_up_date: string | null }
interface PrescriptionItem { id?: string; medicine_name: string; dosage: string; frequency: string; duration: string; route: string | null; notes: string | null }
interface Prescription { id: string; instructions: string | null; items: PrescriptionItem[] }
interface Medicine { medicine_name: string; dosage: string; frequency: string; duration: string; route: string; notes: string }
const blankMedicine: Medicine = { medicine_name: '', dosage: '', frequency: '', duration: '', route: '', notes: '' }

export function ClinicalCarePage() {
  const { appointmentId = '' } = useParams()
  const { t } = useLanguage()
  const speciesLabel = useSpeciesLabel()
  const queryClient = useQueryClient()
  const appointment = useQuery({ queryKey: ['appointment', appointmentId], queryFn: () => api.get<Appointment>(`/appointments/${appointmentId}`) })
  const consultation = useQuery({ queryKey: ['consultation', appointmentId], queryFn: () => api.getOptional<Consultation>(`/appointments/${appointmentId}/consultation`) })
  const prescription = useQuery({
    queryKey: ['prescription', consultation.data?.id],
    queryFn: () => api.getOptional<Prescription>(`/consultations/${consultation.data!.id}/prescription`),
    enabled: Boolean(consultation.data?.id),
  })

  const [editing, setEditing] = useState(false)
  const [initialized, setInitialized] = useState(false)
  const [diagnosis, setDiagnosis] = useState(''); const [notes, setNotes] = useState(''); const [summary, setSummary] = useState(''); const [followUp, setFollowUp] = useState('')
  const [medicines, setMedicines] = useState<Medicine[]>([{ ...blankMedicine }]); const [instructions, setInstructions] = useState(''); const [message, setMessage] = useState<string | null>(null)

  // Start in view mode once we know whether a record already exists — edit mode only by default
  // for a brand-new, never-saved consultation. Only runs once so a background refetch mid-edit
  // doesn't yank the doctor back out of the form.
  useEffect(() => {
    if (!initialized && !consultation.isLoading) {
      setEditing(!consultation.data)
      setInitialized(true)
    }
  }, [initialized, consultation.isLoading, consultation.data])

  useEffect(() => {
    if (consultation.data) {
      setDiagnosis(consultation.data.diagnosis ?? '')
      setNotes(consultation.data.doctor_notes ?? '')
      setSummary(consultation.data.approved_summary ?? '')
      setFollowUp(consultation.data.follow_up_date ?? '')
    }
  }, [consultation.data])

  useEffect(() => {
    if (prescription.data) {
      setInstructions(prescription.data.instructions ?? '')
      setMedicines(
        prescription.data.items.length > 0
          ? prescription.data.items.map((item) => ({
              medicine_name: item.medicine_name,
              dosage: item.dosage,
              frequency: item.frequency,
              duration: item.duration,
              route: item.route ?? '',
              notes: item.notes ?? '',
            }))
          : [{ ...blankMedicine }],
      )
    }
  }, [prescription.data])

  const save = useMutation({
    mutationFn: async () => {
      const payload = { diagnosis, doctor_notes: notes, approved_summary: summary, follow_up_date: followUp || null }
      const record = consultation.data
        ? await api.patch<Consultation>(`/doctor/consultations/${consultation.data.id}`, payload)
        : await api.post<Consultation>(`/appointments/${appointmentId}/consultation`, payload)
      await api.put(`/doctor/consultations/${record.id}/prescription`, {
        instructions: instructions || null,
        recommended_tests: [],
        items: medicines.map((item) => ({ ...item, route: item.route || null, notes: item.notes || null })),
      })
      return record
    },
    onSuccess: async () => {
      setMessage(t('care.savedMessage'))
      await queryClient.invalidateQueries({ queryKey: ['consultation', appointmentId] })
      await queryClient.invalidateQueries({ queryKey: ['prescription'] })
      setEditing(false)
    },
    onError: (error) => setMessage(error instanceof Error ? error.message : t('care.saveError')),
  })

  function submit(event: FormEvent) { event.preventDefault(); save.mutate() }
  function startEditing() { setMessage(null); setEditing(true) }

  if (consultation.isLoading || appointment.isLoading) return <div className="page-content"><LoadingBlock /></div>
  const patient = appointment.data
  const hasSavedRecord = Boolean(consultation.data)

  return <div className="page-content"><Link className="back-link" to="/app/appointments"><ArrowLeft size={18} />{t('care.backToAppointments')}</Link><header className="page-heading clinical-heading split"><div><span className="eyebrow">{t('care.eyebrow')}</span><h1>{patient ? `${patient.owner_name} — ${speciesLabel(patient.species)} visit` : t('care.defaultHeading')}</h1><p>{patient ? patient.owner_mobile_number : t('care.defaultSubtitle')}</p></div>{hasSavedRecord && !editing && <button type="button" className="button secondary" onClick={startEditing}><Pencil size={16} />{t('care.edit')}</button>}</header>

    {!editing && hasSavedRecord ? <>
      <section className="clinical-panel"><div className="panel-title"><Stethoscope /><div><h2>{t('care.assessmentTitle')}</h2><p>{t('care.assessmentSubtitle')}</p></div></div>
        <div className="form-grid"><div><span className="field-label">{t('care.diagnosisLabel')}</span><p>{consultation.data?.diagnosis || t('care.notSet')}</p></div><div><span className="field-label">{t('care.notesLabel')}</span><p>{consultation.data?.doctor_notes || t('care.notSet')}</p></div><div className="span-two"><span className="field-label">{t('care.summaryLabel')}</span><p>{consultation.data?.approved_summary || t('care.notSet')}</p></div>{consultation.data?.follow_up_date && <div><span className="field-label"><CalendarClock size={14} /> {t('care.followUp')}</span><p>{new Date(consultation.data.follow_up_date).toLocaleDateString()}</p></div>}</div>
      </section>
      <section className="clinical-panel"><div className="panel-title"><Pill /><div><h2>{t('care.prescriptionTitle')}</h2><p>{t('care.prescriptionViewSubtitle')}</p></div></div>
        {prescription.isLoading ? <LoadingBlock /> : prescription.data && prescription.data.items.length > 0 ? <>
          <div className="prescription-list">{prescription.data.items.map((item, index) => <div className="medicine-row view" key={item.id ?? index}><div><span className="field-label">{t('care.medicineLabel')}</span><p>{item.medicine_name}</p></div><div><span className="field-label">{t('care.dosageLabel')}</span><p>{item.dosage}</p></div><div><span className="field-label">{t('care.frequencyLabel')}</span><p>{item.frequency}</p></div><div><span className="field-label">{t('care.durationLabel')}</span><p>{item.duration}</p></div><div><span className="field-label">{t('care.routeLabel')}</span><p>{item.route || t('care.notSet')}</p></div></div>)}</div>
          {prescription.data.instructions && <div style={{ marginTop: 14 }}><span className="field-label">{t('care.generalInstructions')}</span><p>{prescription.data.instructions}</p></div>}
        </> : <p className="muted">{t('care.noPrescription')}</p>}
      </section>
    </> : (
      <form className="clinical-form" onSubmit={submit}><section className="clinical-panel"><div className="panel-title"><Stethoscope /><div><h2>{t('care.assessmentTitle')}</h2><p>{t('care.assessmentSubtitle')}</p></div></div><div className="form-grid"><label>{t('care.diagnosisLabel')}<textarea value={diagnosis} onChange={(e) => setDiagnosis(e.target.value)} placeholder={t('care.diagnosisPlaceholder')} /></label><label>{t('care.notesLabel')}<textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder={t('care.notesPlaceholder')} /></label><label className="span-two">{t('care.summaryLabel')}<textarea value={summary} onChange={(e) => setSummary(e.target.value)} placeholder={t('care.summaryPlaceholder')} /></label><label>{t('care.followUpLabel')}<input type="date" value={followUp} min={new Date().toISOString().slice(0,10)} onChange={(e) => setFollowUp(e.target.value)} /></label></div></section>
        <section className="clinical-panel"><div className="panel-title"><Plus /><div><h2>{t('care.prescriptionTitle')}</h2><p>{t('care.prescriptionEditSubtitle')}</p></div></div>{medicines.map((medicine, index) => <div className="medicine-row" key={index}><label>{t('care.medicineLabel')}<input required value={medicine.medicine_name} onChange={(e) => setMedicines(medicines.map((m,i) => i === index ? {...m, medicine_name:e.target.value}:m))} /></label><label>{t('care.dosageLabel')}<input required value={medicine.dosage} placeholder={t('care.dosagePlaceholder')} onChange={(e) => setMedicines(medicines.map((m,i) => i === index ? {...m, dosage:e.target.value}:m))} /></label><label>{t('care.frequencyLabel')}<input required value={medicine.frequency} placeholder={t('care.frequencyPlaceholder')} onChange={(e) => setMedicines(medicines.map((m,i) => i === index ? {...m, frequency:e.target.value}:m))} /></label><label>{t('care.durationLabel')}<input required value={medicine.duration} placeholder={t('care.durationPlaceholder')} onChange={(e) => setMedicines(medicines.map((m,i) => i === index ? {...m, duration:e.target.value}:m))} /></label><label>{t('care.routeLabel')}<input value={medicine.route} placeholder={t('care.routePlaceholder')} onChange={(e) => setMedicines(medicines.map((m,i) => i === index ? {...m, route:e.target.value}:m))} /></label>{medicines.length > 1 && <button type="button" className="icon-button medicine-delete" onClick={() => setMedicines(medicines.filter((_,i) => i !== index))}><Trash2 /></button>}</div>)}<button type="button" className="text-button" onClick={() => setMedicines([...medicines, {...blankMedicine}])}><Plus size={16} /> {t('care.addMedicine')}</button><label>{t('care.instructionsLabel')}<textarea value={instructions} onChange={(e) => setInstructions(e.target.value)} placeholder={t('care.instructionsPlaceholder')} /></label></section>
        {message && <div className={save.isError ? 'inline-error' : 'success-banner'}>{message}</div>}
        <div style={{ display: 'flex', gap: 10 }}>
          {hasSavedRecord && <button type="button" className="button secondary" onClick={() => setEditing(false)}>{t('care.cancel')}</button>}
          <button className="button primary save-clinical" disabled={save.isPending}><Save />{save.isPending ? t('care.saving') : t('care.save')}</button>
        </div>
      </form>
    )}
    <Link className="button secondary" style={{ marginTop: 18 }} to={`/app/messages/${appointmentId}`}><MessageCircle size={17} />{t('care.chatWithOwner')}</Link>
  </div>
}
