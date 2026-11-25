"""Excel/CSV lead import pipeline: parsing, column auto-mapping, validation,
duplicate detection and chunked DB writes."""

import csv
import io

import openpyxl

from apps.leads.models import StudentLead, normalize_phone_number

TARGET_FIELDS = {
    "student_name": "Student Name",
    "student_phone": "Student Phone Number (required)",
    "parent_name": "Parent Name",
    "parent_phone": "Parent Phone Number",
    "email": "Email",
    "district": "District",
    "location": "Location",
    "qualification": "Qualification",
    "previous_school": "School / Previous College",
    "interested_course_name": "Interested Course",
    "lead_source_name": "Lead Source",
    "academic_year_name": "Academic Year",
    "remarks": "Remarks",
}

REQUIRED_FIELDS = {"student_phone"}

# normalized header -> target field, used for auto-mapping
HEADER_ALIASES = {
    "studentname": "student_name", "name": "student_name", "student": "student_name",
    "studentphonenumber": "student_phone", "studentphone": "student_phone",
    "phone": "student_phone", "phonenumber": "student_phone", "mobile": "student_phone",
    "mobilenumber": "student_phone",
    "parentname": "parent_name", "guardianname": "parent_name",
    "parentphonenumber": "parent_phone", "parentphone": "parent_phone", "guardianphone": "parent_phone",
    "email": "email", "emailaddress": "email",
    "district": "district",
    "location": "location", "city": "location", "address": "location",
    "qualification": "qualification",
    "school": "previous_school", "previouscollege": "previous_school", "schoolpreviouscollege": "previous_school",
    "interestedcourse": "interested_course_name", "course": "interested_course_name",
    "leadsource": "lead_source_name", "source": "lead_source_name",
    "academicyear": "academic_year_name", "year": "academic_year_name",
    "remarks": "remarks", "notes": "remarks", "comments": "remarks",
}


def _normalize_header(header: str) -> str:
    return "".join(ch for ch in header.lower().strip() if ch.isalnum())


def read_rows(file_field):
    """Read an uploaded CSV/XLSX file. Returns (headers, list_of_row_dicts)."""
    name = file_field.name.lower()
    file_field.open("rb")
    try:
        raw = file_field.read()
    finally:
        file_field.close()

    if name.endswith(".csv"):
        text = raw.decode("utf-8-sig", errors="replace")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            return [], []
        headers = [h.strip() for h in rows[0]]
        data_rows = []
        for r in rows[1:]:
            if not any(cell.strip() for cell in r if cell):
                continue
            row = {headers[i]: (r[i].strip() if i < len(r) else "") for i in range(len(headers))}
            data_rows.append(row)
        return headers, data_rows

    # xlsx
    workbook = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    sheet = workbook.active
    rows_iter = sheet.iter_rows(values_only=True)
    try:
        header_row = next(rows_iter)
    except StopIteration:
        return [], []
    headers = [str(h).strip() if h is not None else "" for h in header_row]
    data_rows = []
    for r in rows_iter:
        if r is None or all(cell in (None, "") for cell in r):
            continue
        row = {}
        for i, h in enumerate(headers):
            value = r[i] if i < len(r) else ""
            row[h] = "" if value is None else str(value).strip()
        data_rows.append(row)
    return headers, data_rows


def guess_column_mapping(headers):
    """Returns {header: target_field_or_''} best-effort auto mapping."""
    mapping = {}
    for header in headers:
        key = _normalize_header(header)
        mapping[header] = HEADER_ALIASES.get(key, "")
    return mapping


def validate_rows(raw_rows, column_mapping):
    """Apply column_mapping (header -> target field) to raw rows, normalize
    phone numbers, and flag invalid / duplicate rows.

    Returns a list of dicts: {"data": {...mapped fields...}, "errors": [...],
    "is_duplicate_in_file": bool, "duplicate_in_db": bool}
    """
    seen_phones = set()
    existing_phones = set(
        StudentLead.objects.filter(is_archived=False).values_list("student_phone_normalized", flat=True)
    )
    results = []

    for raw_row in raw_rows:
        mapped = {}
        for header, target in column_mapping.items():
            if target:
                mapped[target] = raw_row.get(header, "")

        errors = []
        phone_raw = mapped.get("student_phone", "")
        phone_norm = normalize_phone_number(phone_raw)

        digit_count = len(phone_norm.lstrip("+"))
        if not phone_raw:
            errors.append("Missing student phone number.")
        elif not phone_norm or digit_count < 7:
            errors.append(f"Invalid phone number format: '{phone_raw}'.")

        is_dup_in_file = bool(phone_norm) and phone_norm in seen_phones
        is_dup_in_db = bool(phone_norm) and phone_norm in existing_phones

        if phone_norm:
            seen_phones.add(phone_norm)

        results.append(
            {
                "data": mapped,
                "phone_normalized": phone_norm,
                "errors": errors,
                "is_duplicate_in_file": is_dup_in_file,
                "is_duplicate_in_db": is_dup_in_db,
                "is_valid": not errors,
            }
        )
    return results


def summarize(validated_rows):
    total = len(validated_rows)
    invalid = sum(1 for r in validated_rows if not r["is_valid"])
    duplicates = sum(1 for r in validated_rows if r["is_duplicate_in_file"] or r["is_duplicate_in_db"])
    valid = total - invalid
    new_leads = sum(
        1
        for r in validated_rows
        if r["is_valid"] and not r["is_duplicate_in_file"] and not r["is_duplicate_in_db"]
    )
    return {
        "total_rows": total,
        "valid_rows": valid,
        "invalid_rows": invalid,
        "duplicate_rows": duplicates,
        "new_leads_count": new_leads,
    }


CHUNK_SIZE = 500


def commit_rows(validated_rows, batch, created_by, lead_source=None, campaign=None, academic_year=None,
                 skip_duplicates=True):
    """Chunked bulk_create of valid, non-duplicate rows. Returns count created."""
    from django.db import transaction

    from apps.courses.models import AcademicSession, Course
    from apps.leads.models import LeadSource

    to_create = [
        r for r in validated_rows
        if r["is_valid"] and not (skip_duplicates and (r["is_duplicate_in_file"] or r["is_duplicate_in_db"]))
    ]

    course_cache = {}
    source_cache = {}
    session_cache = {}
    created_count = 0

    for start in range(0, len(to_create), CHUNK_SIZE):
        chunk = to_create[start:start + CHUNK_SIZE]
        objs = []
        seen_in_chunk = set()
        for row in chunk:
            data = row["data"]
            phone_norm = row["phone_normalized"]
            if phone_norm in seen_in_chunk:
                continue
            seen_in_chunk.add(phone_norm)

            course = None
            course_name = data.get("interested_course_name", "").strip()
            if course_name:
                if course_name not in course_cache:
                    course_cache[course_name] = Course.objects.filter(name__iexact=course_name).first()
                course = course_cache[course_name]

            source = lead_source
            source_name = data.get("lead_source_name", "").strip()
            if not source and source_name:
                if source_name not in source_cache:
                    source_cache[source_name], _ = LeadSource.objects.get_or_create(name=source_name)
                source = source_cache[source_name]

            session = academic_year
            session_name = data.get("academic_year_name", "").strip()
            if not session and session_name:
                if session_name not in session_cache:
                    session_cache[session_name] = AcademicSession.objects.filter(name__iexact=session_name).first()
                session = session_cache[session_name]

            objs.append(
                StudentLead(
                    student_name=data.get("student_name", "").strip() or "Unknown Student",
                    student_phone=data.get("student_phone", "").strip(),
                    student_phone_normalized=phone_norm,
                    parent_name=data.get("parent_name", "").strip(),
                    parent_phone=data.get("parent_phone", "").strip(),
                    parent_phone_normalized=normalize_phone_number(data.get("parent_phone", "")),
                    email=data.get("email", "").strip(),
                    district=data.get("district", "").strip(),
                    location=data.get("location", "").strip(),
                    qualification=data.get("qualification", "").strip(),
                    previous_school=data.get("previous_school", "").strip(),
                    interested_course=course,
                    lead_source=source,
                    campaign=campaign,
                    academic_year=session,
                    remarks=data.get("remarks", "").strip(),
                    import_batch=batch,
                    created_by=created_by,
                )
            )
        with transaction.atomic():
            StudentLead.objects.bulk_create(objs)
        created_count += len(objs)

    return created_count
