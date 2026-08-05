import json
import re
import uuid
from typing import Optional

from langdetect import detect, LangDetectException

from app.llm.client import gemini_client
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    ResponseIntent,
)
from app.safety.guardrails import assess_safety
from app.services.conversation import conversation_store
from app.tools.facilities import (
    FacilityServiceError,
    search_facilities,
)
from app.tools.govt_schemes import (
    search_government_schemes,
)
from app.tools.anganwadi import (
    infer_community_worker,
    get_community_health_support,
)
from app.tools.reminders import (
    create_reminder,
)
from app.tools.medicines import (
    search_medicines,
    MedicineServiceError,
)
from app.tools.home_remedies import (
    search_home_remedies,
    HomeRemedyServiceError,
)
from app.tools.ambulances import (
    get_nearby_ambulances,
    AmbulanceServiceError,
)
from app.tools.appointments import (
    get_appointments,
    create_appointment,
    AppointmentServiceError,
)


def detect_language(text: str) -> str | None:
    try:
        return detect(text)
    except LangDetectException:
        return None


def infer_basic_intent(
    message: str,
    emergency: bool,
) -> ResponseIntent:

    if emergency:
        return ResponseIntent.EMERGENCY

    text = message.lower().strip()

    # --------------------------------------------------
    # KEYWORD GROUPS
    # --------------------------------------------------

    anganwadi_words = [
        "anganwadi",
        "anganwadi worker",
        "anganwadi centre",
        "anganwadi center",
        "asha worker",
        "asha didi",
        "health worker",
    ]

    explicit_scheme_words = [
        "scheme",
        "schemes",
        "yojana",
        "government scheme",
        "government schemes",
        "government benefit",
        "government benefits",
        "government support",
        "government assistance",
        "government help",
        "sarkari yojana",
        "sarkari scheme",
        "sarkari madad",
        "sarkar se madad",
        "pmmvy",
        "pradhan mantri matru vandana",
        "janani suraksha",
        "jsy",
    ]

    reminder_words = [
        "remind me",
        "reminder",
        "medication reminder",
        "medicine reminder",
        "medicine schedule",
        "medication schedule",
    ]

    facility_words = [
        "hospital",
        "hospitals",
        "clinic",
        "clinics",
        "phc",
        "bphc",
        "health centre",
        "health center",
        "pharmacy",
        "medical store",
        "lab",
        "laboratory",
        "nearby",
        "near me",
    ]

    medicine_words = [
    "medicine",
    "medicines",
    "tablet",
    "tablets",
    "capsule",
    "capsules",
    "drug",
    "drugs",
    "paracetamol",
    "ibuprofen",
    "crocin",
    "dolo",
    "amoxicillin",
    "what medicine",
    "which medicine",
]

    home_remedy_words = [
    "home remedy",
    "home remedies",
    "natural remedy",
    "natural remedies",
    "remedy",
    "remedies",
    "kadha",
    "home treatment",
]

    ambulance_words = [
    "ambulance",
    "ambulances",
    "emergency vehicle",
]

    appointment_words = [
    "appointment",
    "book appointment",
    "schedule appointment",
    "doctor appointment",
]


    maternity_context_words = [
        "pregnant",
        "pregnancy",
        "maternity",
        "expecting a baby",
        "expecting child",
        "delivery",
        "childbirth",
        "giving birth",
        "new mother",
        "lactating",
        "breastfeeding mother",
        "garbhavati",
        "pregnancy ke time",
        "delivery ke time",
    ]

    assistance_context_words = [
        "financial help",
        "financial support",
        "financial assistance",
        "money help",
        "cash assistance",
        "cash benefit",
        "benefit",
        "benefits",
        "support available",
        "help available",
        "assistance available",
        "low income",
        "poor family",
        "cannot afford",
        "can't afford",
        "cant afford",
        "afford pregnancy",
        "afford delivery",
        "pregnancy expenses",
        "delivery expenses",
        "medical expenses",
        "financial problem",
        "financial difficulty",
        "paise ki dikkat",
        "paison ki dikkat",
        "arthik madad",
        "madad mil sakti",
        "madad milegi",
        "koi madad",
    ]

    # --------------------------------------------------
    # 1. COMMUNITY HEALTH WORKER
    # --------------------------------------------------

    if any(
        word in text
        for word in anganwadi_words
    ):
        return ResponseIntent.ANGANWADI

    # --------------------------------------------------
    # 2. EXPLICIT GOVERNMENT SCHEME REQUEST
    # --------------------------------------------------

    if any(
        word in text
        for word in explicit_scheme_words
    ):
        return ResponseIntent.GOVERNMENT_SCHEME

    # --------------------------------------------------
    # 3. IMPLICIT GOVERNMENT SCHEME REQUEST
    # --------------------------------------------------
    #
    # IMPORTANT:
    # This runs BEFORE facility detection.
    #
    # Pregnancy/maternity context alone is NOT enough.
    # Financial/support context must also exist.
    # --------------------------------------------------

    has_maternity_context = any(
        word in text
        for word in maternity_context_words
    )

    has_assistance_context = any(
        word in text
        for word in assistance_context_words
    )

    if (
        has_maternity_context
        and has_assistance_context
    ):
        return ResponseIntent.GOVERNMENT_SCHEME

    # --------------------------------------------------
    # 4. REMINDER
    # --------------------------------------------------

    if any(
        word in text
        for word in reminder_words
    ):
        return ResponseIntent.REMINDER

    # --------------------------------------------------
    #  MEDICINE
    # --------------------------------------------------
    if any(
        word in text
        for word in medicine_words
        ):
        return ResponseIntent.MEDICINE

    # ---------------------------------------------------
    # HOME REMEDIES
    # ---------------------------------------------------

    if any(
    word in text
    for word in home_remedy_words
    ):
        return ResponseIntent.HOME_REMEDY

    # ----------------------------------------------------
    # AMBULANCE
    # ----------------------------------------------------

    if any(
    word in text
    for word in ambulance_words
    ):
        return ResponseIntent.AMBULANCE

    # ---------------------------------------------------
    # APPOINTMENTS
    # ---------------------------------------------------

    if any(
    word in text
    for word in appointment_words
    ):
        return ResponseIntent.APPOINTMENT
    
    # --------------------------------------------------
    # 5. FACILITY SEARCH
    # --------------------------------------------------

    if any(
        word in text
        for word in facility_words
    ):
        return ResponseIntent.FACILITY_SEARCH

    # --------------------------------------------------
    # 6. DEFAULT HEALTH GUIDANCE
    # --------------------------------------------------

    return ResponseIntent.HEALTH_GUIDANCE


def infer_facility_type(
    message: str,
) -> Optional[str]:

    text = message.lower()

    if (
        "phc" in text
        or "bphc" in text
        or "primary health centre" in text
        or "primary health center" in text
    ):
        return "phc"

    if (
        "hospital" in text
        or "hospitals" in text
    ):
        return "hospital"

    return None


def extract_location_hint(
    message: str,
) -> Optional[str]:
    """
    Very small V1 location extractor.

    This is intentionally conservative. Later Gemini structured
    extraction / frontend geolocation will replace this.
    """

    patterns = [
        r"\bin\s+([A-Za-z][A-Za-z\s]{1,50})$",
        r"\bnear\s+([A-Za-z][A-Za-z\s]{1,50})$",
        r"\baround\s+([A-Za-z][A-Za-z\s]{1,50})$",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            message.strip(),
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(1).strip()

    return None


def extract_location_hint(
    message: str,
) -> Optional[str]:
    """
    Extract a possible location from a facility request.

    This is a conservative V1 extractor. The extracted value is
    passed to the existing facility API as a city first.

    Examples:
        "hospitals in Pune" -> "Pune"
        "PHCs near Noida" -> "Noida"
        "hospital around Lucknow" -> "Lucknow"

    Requests such as "hospital near me" intentionally return None
    because we do not currently have the user's GPS location.
    """

    text = message.strip()

    # Do not interpret "me", "my area", etc. as actual locations.
    generic_location_phrases = [
        r"\bnear\s+me\b",
        r"\bnearby\b",
        r"\bin\s+my\s+area\b",
        r"\baround\s+me\b",
        r"\bclose\s+to\s+me\b",
    ]

    for pattern in generic_location_phrases:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return None

    patterns = [
        r"\bin\s+([A-Za-z][A-Za-z\s]{1,50}?)(?:\?|\.|!|$)",
        r"\bnear\s+([A-Za-z][A-Za-z\s]{1,50}?)(?:\?|\.|!|$)",
        r"\baround\s+([A-Za-z][A-Za-z\s]{1,50}?)(?:\?|\.|!|$)",
        r"\bat\s+([A-Za-z][A-Za-z\s]{1,50}?)(?:\?|\.|!|$)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            location = match.group(1).strip()

            # Remove common trailing words that are not
            # actually part of the location.
            location = re.sub(
                r"\s+(please|pls)$",
                "",
                location,
                flags=re.IGNORECASE,
            ).strip()

            if location:
                return location

    return None

async def search_facilities_with_location_fallback(
    facility_type: str,
    location: str,
    limit: int = 5,
) -> dict:
    """
    Search using the existing backend without requiring any
    backend changes.

    Since a user may provide a city, district, or state without
    explicitly saying which one it is, try the existing API
    filters in this order:

        city -> district -> state

    Stop as soon as matching facilities are found.
    """

    search_attempts = [
        {
            "city": location,
        },
        {
            "district": location,
        },
        {
            "state": location,
        },
    ]

    for filters in search_attempts:
        result = await search_facilities(
            facility_type=facility_type,
            limit=limit,
            **filters,
        )

        if (
            result.get("success")
            and result.get("facilities")
        ):
            result["matched_location_as"] = next(
                iter(filters.keys())
            )

            return result

    return {
        "success": True,
        "count": 0,
        "facilities": [],
        "matched_location_as": None,
    }

def build_facility_context(
    facility_data: dict,
) -> str:
    """
    Convert verified facility-tool results into context
    that can safely be provided to Gemini.
    """

    if not facility_data.get("success"):
        return (
            "The facility tool could not provide verified "
            "facility results."
        )

    facilities = facility_data.get(
        "facilities",
        []
    )

    if not facilities:
        return (
            "The SahiSehat facility database returned no "
            "matching facilities."
        )

    return (
        "VERIFIED SAHISEHAT FACILITY DATA:\n"
        + json.dumps(
            facilities,
            ensure_ascii=False,
            indent=2,
        )
        + "\n\n"
        "Use ONLY these facility records when mentioning "
        "specific healthcare facilities. "
        "Do not invent additional facility names, addresses, "
        "coordinates, services, ownership information, "
        "distances, or other details."
    )

def build_scheme_context(
    scheme_data: dict,
) -> str:
    """
    Convert verified government-scheme records into
    controlled context for Gemini.
    """

    schemes = scheme_data.get(
        "schemes",
        []
    )

    if not schemes:
        return (
            "No matching government scheme was found in "
            "SahiSehat's currently verified scheme records."
        )

    return (
        "VERIFIED GOVERNMENT SCHEME DATA:\n"
        + json.dumps(
            schemes,
            ensure_ascii=False,
            indent=2,
        )
        + "\n\n"
        "Use ONLY this verified data for factual claims "
        "about scheme benefits, eligibility, conditions, "
        "application procedures, and administering bodies."
    )

def build_community_health_context(
    community_data: dict,
) -> str:
    """
    Convert verified Anganwadi/ASHA capability information
    into controlled context for Gemini.

    This data describes what community health workers can
    generally help with. It does NOT represent a live directory
    of specific workers or centres.
    """

    workers = community_data.get(
        "workers",
        []
    )

    if not workers:
        return (
            "No matching community health worker information "
            "was found in SahiSehat's currently available "
            "support records."
        )

    return (
        "VERIFIED SAHISEHAT COMMUNITY HEALTH SUPPORT DATA:\n"
        + json.dumps(
            workers,
            ensure_ascii=False,
            indent=2,
        )
        + "\n\n"
        "Use ONLY this information when explaining what "
        "Anganwadi or ASHA workers can help with. "
        "This is capability information, NOT a live directory. "
        "Do not invent worker names, phone numbers, addresses, "
        "centre locations, availability, or contact details."
    )

def build_reminder_context(
    reminder_data: dict,
) -> str:

    reminder = reminder_data.get(
        "reminder",
        {}
    )

    missing_fields = reminder_data.get(
        "missing_fields",
        []
    )

    return (
        "SAHISEHAT REMINDER REQUEST:\n"
        + json.dumps(
            reminder,
            ensure_ascii=False,
            indent=2,
        )
        + "\n\n"
        + "MISSING FIELDS:\n"
        + json.dumps(
            missing_fields,
            ensure_ascii=False,
        )
        + "\n\n"
        + "IMPORTANT: This reminder has only been prepared "
        "inside Sathi. Persistent reminder delivery is NOT "
        "currently connected."
    )

def build_medicine_context(
    medicine_data: dict,
) -> str:

    medicines = medicine_data.get(
        "medicines",
        []
    )

    if not medicines:

        return (
            "No matching medicines were found "
            "in the verified SahiSehat medicine database."
        )

    return (
        "VERIFIED SAHISEHAT MEDICINE DATA:\n"
        + json.dumps(
            medicines,
            ensure_ascii=False,
            indent=2,
        )
        + "\n\n"
        + "Use ONLY these verified medicines."
    )

def build_home_remedy_context(
    remedy_data: dict,
) -> str:

    remedies = remedy_data.get(
        "remedies",
        []
    )

    if not remedies:
        return (
            "No verified home remedies were found."
        )

    return (
        "VERIFIED HOME REMEDIES:\n"
        + json.dumps(
            remedies,
            ensure_ascii=False,
            indent=2,
        )
    )

def build_ambulance_context(
    ambulance_data: dict,
) -> str:

    ambulances = ambulance_data.get(
        "ambulances",
        []
    )

    if not ambulances:
        return (
            "No nearby ambulances were found."
        )

    return (
        "VERIFIED AMBULANCE DATA:\n"
        + json.dumps(
            ambulances,
            ensure_ascii=False,
            indent=2,
        )
    )

def build_appointment_context(
    appointment_data: dict,
) -> str:

    appointments = appointment_data.get(
        "appointments",
        []
    )

    return (
        "VERIFIED APPOINTMENTS:\n"
        + json.dumps(
            appointments,
            ensure_ascii=False,
            indent=2,
        )
    )

# ============================================================
# FRONTEND ACTION MAPPER
# ============================================================

def get_frontend_action(intent):

    page_map = {

        ResponseIntent.FACILITY: "view-centres",

        ResponseIntent.GOVERNMENT_SCHEME: "view-schemes",

        ResponseIntent.APPOINTMENT: "view-appointments",

        ResponseIntent.PROFILE: "view-profile",

        ResponseIntent.MEDICAL_RECORD: "view-records",

        ResponseIntent.FAMILY: "view-family",

        ResponseIntent.DASHBOARD: "view-dashboard",

    }

    page = page_map.get(intent)

    if page is None:
        return None

    return {
        "type": "OPEN_PAGE",
        "page": page,
    }

async def process_chat(
    request: ChatRequest,
) -> ChatResponse:

    session_id = (
        request.session_id
        or str(uuid.uuid4())
    )

    language = (
        request.language
        or detect_language(request.message)
    )

    safety = assess_safety(
        request.message
    )

    intent = infer_basic_intent(
        request.message,
        safety.emergency,
    )

    history = conversation_store.get_history(
        session_id
    )

    message_for_gemini = request.message

    # --------------------------------------------------
    # FACILITY TOOL
    # --------------------------------------------------

    if (
        intent == ResponseIntent.FACILITY_SEARCH
        and not safety.emergency
    ):

        facility_type = infer_facility_type(
            request.message
        )

        if facility_type:

            location_hint = extract_location_hint(
                request.message
            )

            try:
                # --------------------------------------
                # User supplied a location
                # --------------------------------------

                if location_hint:

                    facility_data = (
                        await search_facilities_with_location_fallback(
                            facility_type=facility_type,
                            location=location_hint,
                            limit=5,
                        )
                    )

                    facility_context = build_facility_context(
                        facility_data
                    )

                    message_for_gemini = f"""
The user asked:

{request.message}

The user provided this location:

{location_hint}

{facility_context}

Answer using ONLY the verified SahiSehat facility data above.

Rules:

- Never invent a healthcare facility.
- Never invent an address, service, phone number, distance,
  coordinate, or ownership value.
- Do not call a facility "nearest" or "closest".
- Do not claim that results are sorted by distance.
- These results match the user's location through the existing
  SahiSehat facility database filters.
- If no facilities were returned, say that no matching facilities
  were found in the currently available records.
- You may ask the user for a different city, district, or state.
- Do not expose database IDs.
- Do not expose raw JSON.
"""

                # --------------------------------------
                # User did NOT supply a location
                # --------------------------------------

                else:

                    message_lower = request.message.lower()

                    wants_nearby = any(
                        phrase in message_lower
                        for phrase in [
                            "near me",
                            "nearby",
                            "my area",
                            "around me",
                            "close to me",
                        ]
                    )

                    if wants_nearby:

                        message_for_gemini = f"""
The user asked:

{request.message}

The user wants nearby healthcare facilities, but Sathi has not
received their current location.

Ask the user for their city, district, or state so that you can
search the existing SahiSehat facility database.

Keep the response short and natural.

Do not invent facilities.

Do not claim to know the user's current location.
"""

                    else:

                        facility_data = await search_facilities(
                            facility_type=facility_type,
                            limit=5,
                        )

                        facility_context = build_facility_context(
                            facility_data
                        )

                        message_for_gemini = f"""
The user asked:

{request.message}

{facility_context}

The user did not specify a location.

You may show these verified facility records, but clearly explain
that they are general database results and are NOT necessarily
near the user.

Ask for a city, district, or state if they want more relevant
results.

Never invent facilities or proximity information.
Do not expose database IDs or raw JSON.
"""

            except FacilityServiceError as exc:

                print(
                    f"Facility tool error: {exc}"
                )

                message_for_gemini = f"""
The user asked:

{request.message}

The SahiSehat healthcare facility service could not be reached.

Briefly explain that specific facility information cannot be
verified right now.

Do not invent healthcare facilities.

The user may try the facility search again shortly.
"""

        else:

            message_for_gemini = f"""
The user appears to be asking for a healthcare facility:

{request.message}

The currently connected SahiSehat facility tool supports
PHCs/BPHCs and hospitals.

Ask whether they would like a PHC/BPHC or a hospital.

Keep the question short.

Do not invent healthcare facilities.
"""

    # --------------------------------------------------
    # GOVERNMENT SCHEME TOOL
    # --------------------------------------------------

    if (
        intent == ResponseIntent.GOVERNMENT_SCHEME
        and not safety.emergency
    ):

        scheme_data = search_government_schemes(
            request.message
        )

        scheme_context = build_scheme_context(
            scheme_data
        )

        message_for_gemini = f"""
The user asked:

{request.message}

{scheme_context}

You are helping the user understand Indian government
health and maternity schemes.

Rules:

- Use ONLY the verified scheme data above for factual
  claims about schemes.
- Never invent a government scheme.
- Never invent benefit amounts.
- Never invent eligibility requirements.
- Never guarantee that the user qualifies.
- Clearly distinguish between "may be eligible" and
  confirmed eligibility.
- If important eligibility information is missing,
  ask the user for only the information necessary to
  help narrow it down.
- Do not ask for Aadhaar numbers, bank account numbers,
  or other sensitive identifiers.
- If relevant, suggest contacting an Anganwadi Worker,
  ASHA worker, or appropriate government health facility.
- Keep the explanation understandable for a general user.
"""

    # --------------------------------------------------
    # ANGANWADI / ASHA COMMUNITY HEALTH TOOL
    # --------------------------------------------------

    if (
        intent == ResponseIntent.ANGANWADI
        and not safety.emergency
    ):

        worker_type = infer_community_worker(
            request.message
        )

        community_data = get_community_health_support(
            worker_type
        )

        community_context = build_community_health_context(
            community_data
        )

        message_for_gemini = f"""
The user asked:

{request.message}

{community_context}

You are helping the user understand community-level health
support available through Anganwadi Workers and ASHA Workers.

Rules:

- Use ONLY the verified community health support information
  above when describing what these workers can help with.
- Never invent an Anganwadi Worker or ASHA Worker.
- Never invent a worker name.
- Never invent a phone number.
- Never invent an Anganwadi centre.
- Never invent an address or location.
- Never claim that a specific worker is currently available.
- Never claim that Sathi has contacted a worker unless an
  actual communication tool has performed that action.
- Never claim that an appointment or visit has been arranged
  unless an actual connected service confirms it.
- Clearly explain that Anganwadi and ASHA workers provide
  community-level support and are not substitutes for emergency
  medical services.
- If the user describes a medical emergency, emergency safety
  handling takes priority over community-worker guidance.
- If the user asks where their nearest Anganwadi centre or
  ASHA worker is, explain that Sathi does not currently have
  verified location-directory data for these workers.
- You may ask for the user's city, district, or state only when
  it would help with another connected SahiSehat service.
- Do not ask for Aadhaar numbers, bank account details, or
  unnecessary sensitive identifiers.
- Keep the response empathetic, simple, and practical.
"""

        # --------------------------------------------------
    # MEDICINE TOOL
    # --------------------------------------------------

    if (
        intent == ResponseIntent.MEDICINE
        and not safety.emergency
    ):

        try:

            medicine_data = await search_medicines(
                request.message
            )

            medicine_context = (
                build_medicine_context(
                    medicine_data
                )
            )

            message_for_gemini = f"""
The user asked:

{request.message}

{medicine_context}

You are helping the user understand medicines.

Rules:

- Use ONLY the verified medicine information above.
- Never invent a medicine.
- Never invent a dosage.
- Never tell the user to start or stop a prescribed medicine.
- Never recommend antibiotics unless they have already been prescribed by a qualified healthcare professional.
- If no verified medicine is found, clearly tell the user.
- If the user asks about dosage, prescription changes, or side effects, recommend consulting a qualified healthcare professional.
- Do not expose raw JSON or internal database fields.
"""

        except MedicineServiceError as exc:

            print(
                f"Medicine tool error: {exc}"
            )

            message_for_gemini = f"""
The user asked:

{request.message}

The SahiSehat medicine service is currently unavailable.

Briefly explain that verified medicine information cannot be retrieved right now.

Do not invent medicine information.
"""

        # --------------------------------------------------
    # HOME REMEDY TOOL
    # --------------------------------------------------

    if (
        intent == ResponseIntent.HOME_REMEDY
        and not safety.emergency
    ):

        try:

            remedy_data = await search_home_remedies(
                query=request.message
            )

            remedy_context = (
                build_home_remedy_context(
                    remedy_data
                )
            )

            message_for_gemini = f"""
The user asked:

{request.message}

{remedy_context}

You are helping the user understand home remedies.

Rules:

- Use ONLY the verified home remedy information above.
- Never invent a home remedy.
- Never claim that a home remedy can cure a disease.
- Recommend only conservative, low-risk remedies.
- If no verified remedy is found, clearly tell the user.
- If symptoms suggest a serious medical condition, advise seeking professional medical care.
- Do not expose raw JSON or internal database fields.
"""

        except HomeRemedyServiceError as exc:

            print(
                f"Home remedy tool error: {exc}"
            )

            message_for_gemini = f"""
The user asked:

{request.message}

The SahiSehat home remedy service is currently unavailable.

Briefly explain that verified home remedy information cannot be retrieved right now.

Do not invent home remedies.
"""

                # --------------------------------------------------
    # AMBULANCE TOOL
    # --------------------------------------------------

    if (
        intent == ResponseIntent.AMBULANCE
        and not safety.emergency
    ):

        try:

            ambulance_data = (
                await get_nearby_ambulances()
            )

            ambulance_context = (
                build_ambulance_context(
                    ambulance_data
                )
            )

            message_for_gemini = f"""
The user asked:

{request.message}

{ambulance_context}

You are helping the user locate nearby ambulances.

Rules:

- Use ONLY the verified ambulance information above.
- Never invent an ambulance.
- Never invent phone numbers.
- Never invent driver names.
- Never invent locations.
- If no ambulances are available, clearly tell the user.
- Do not expose raw JSON or internal database fields.
"""

        except AmbulanceServiceError as exc:

            print(
                f"Ambulance tool error: {exc}"
            )

            message_for_gemini = f"""
The user asked:

{request.message}

The SahiSehat ambulance service is currently unavailable.

Briefly explain that verified ambulance information cannot be retrieved right now.

Do not invent ambulance information.
"""

                # --------------------------------------------------
    # APPOINTMENT TOOL
    # --------------------------------------------------

    if (
        intent == ResponseIntent.APPOINTMENT
        and not safety.emergency
    ):

        try:

            appointment_data = (
                await get_appointments(
                    request.token
                )
            )

            appointment_context = (
                build_appointment_context(
                    appointment_data
                )
            )

            message_for_gemini = f"""
The user asked:

{request.message}

{appointment_context}

You are helping the user understand their appointments.

Rules:

- Use ONLY the verified appointment information above.
- Never invent appointments.
- Never invent appointment dates or times.
- Never claim an appointment has been booked unless confirmed by the appointment service.
- Do not expose raw JSON or internal database fields.
"""

        except AppointmentServiceError as exc:

            print(
                f"Appointment tool error: {exc}"
            )

            message_for_gemini = f"""
The user asked:

{request.message}

The SahiSehat appointment service is currently unavailable.

Briefly explain that appointment information cannot be retrieved right now.

Do not invent appointment information.
"""

    # --------------------------------------------------
    # REMINDER TOOL
    # --------------------------------------------------

    if (
        intent == ResponseIntent.REMINDER
        and not safety.emergency
    ):

        reminder_data = create_reminder(
            session_id=session_id,
            message=request.message,
        )

        reminder_context = build_reminder_context(
            reminder_data
        )

        message_for_gemini = f"""
The user asked:

{request.message}

{reminder_context}

You are helping the user prepare a health-related reminder.

Rules:

- Never claim that the reminder has actually been scheduled.
- Never claim that Sathi will send a notification yet.
- Never claim that an SMS, WhatsApp message, push notification,
  phone call, or voice alert has been configured.
- The current reminder is only a structured draft.
- If the reminder is missing a time, ask the user what time
  they want the reminder.
- If a time was successfully detected, confirm what Sathi
  understood.
- If a frequency was detected, confirm the frequency.
- If frequency was not specified, do not invent one.
- Do not recommend medication dosages.
- Do not change a medication schedule prescribed by a doctor.
- If the user asks what dose they should take, treat that as
  a health/medication-safety question rather than inventing
  instructions.
- Explain briefly that reminder delivery will become active
  once SahiSehat's notification system is connected.
- Keep the response short and clear.
"""


    # --------------------------------------------------
    # GEMINI
    # --------------------------------------------------

    response_text = await gemini_client.generate_response(
        message=message_for_gemini,
        history=history,
    )
    print(repr(response_text))

    conversation_store.add_message(
        session_id=session_id,
        role="user",
        content=request.message,
    )

    conversation_store.add_message(
        session_id=session_id,
        role="assistant",
        content=response_text,
    )

    return ChatResponse(
        session_id=session_id,
        response=response_text,
        detected_language=language,
        intent=intent,
        risk_level=safety.risk_level,
        requires_professional_care=(
            safety.requires_professional_care
        ),
        emergency=safety.emergency,
    )