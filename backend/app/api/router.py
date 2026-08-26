from fastapi import APIRouter

from app.api.routes.admin import router as admin_router
from app.api.routes.appointments import router as appointments_router
from app.api.routes.attachments import router as attachments_router
from app.api.routes.auth import router as auth_router
from app.api.routes.calls import router as calls_router
from app.api.routes.consultations import router as consultations_router
from app.api.routes.doctors import router as doctors_router
from app.api.routes.events import router as events_router
from app.api.routes.health import router as health_router
from app.api.routes.medical_records import router as medical_records_router
from app.api.routes.messages import router as messages_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.payments import router as payments_router
from app.api.routes.pets import router as pets_router
from app.api.routes.pricing import router as pricing_router
from app.api.routes.recordings import router as recordings_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["system"])
api_router.include_router(auth_router, tags=["authentication"])
api_router.include_router(pets_router, tags=["pets"])
api_router.include_router(doctors_router, tags=["doctors"])
api_router.include_router(pricing_router, tags=["pricing"])
api_router.include_router(calls_router, tags=["calls"])
api_router.include_router(events_router, tags=["realtime events"])
api_router.include_router(admin_router, tags=["administration"])
api_router.include_router(appointments_router, tags=["appointments"])
api_router.include_router(medical_records_router, tags=["medical records"])
api_router.include_router(consultations_router, tags=["consultations"])
api_router.include_router(attachments_router, tags=["consultation attachments"])
api_router.include_router(messages_router, tags=["appointment chat"])
api_router.include_router(notifications_router, tags=["reminders and notifications"])
api_router.include_router(recordings_router, tags=["call recordings"])
api_router.include_router(payments_router, tags=["payments"])
