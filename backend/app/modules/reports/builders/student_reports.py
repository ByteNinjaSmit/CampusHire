"""STUDENT report builders: my-applications, interview-schedule, placement-status (ADMIN may pass student_id)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.applications.models import Application, ApplicationStatusHistory
from app.modules.companies.models import Company
from app.modules.internships.models import Internship
from app.modules.interviews.models import Interview
from app.modules.reports.builders.common import (
    APPLICATION_STATUSES,
    OPEN_STATUSES,
    TABLE_ROW_CAP,
    internship_filters,
    iso,
    kpi,
    now_utc,
    num,
    parse_params,
    pie_chart,
    student_target,
    table,
)
from app.modules.reports.schemas import ReportData
from app.modules.users.models import User


# =========================================================================== my-applications
async def build_my_applications(session: AsyncSession, user: User, params: dict[str, Any]) -> ReportData:
    f = parse_params(params)
    sid = student_target(user, f)
    A, I, C, H = Application, Internship, Company, ApplicationStatusHistory
    conds = [A.student_id == sid, *f.apply(A.created_at), *internship_filters(f)]

    apps = (
        await session.execute(
            select(A.id, A.status, A.created_at, A.status_changed_at, I.title, C.name)
            .select_from(A)
            .join(I, I.id == A.internship_id)
            .join(C, C.id == I.company_id)
            .where(*conds)
            .order_by(A.created_at.desc())
            .limit(TABLE_ROW_CAP)
        )
    ).all()
    by_status = {s: 0 for s in APPLICATION_STATUSES}
    for a in apps:
        by_status[a.status] += 1

    hist = (
        await session.execute(
            select(H.application_id, H.to_status, H.created_at, H.note)
            .where(H.application_id.in_([a.id for a in apps]) if apps else H.id < 0)
            .order_by(H.created_at)
        )
    ).all()
    hist_by_app: dict[Any, list[Any]] = {}
    for h in hist:
        hist_by_app.setdefault(h.application_id, []).append(h)

    events: list[dict[str, Any]] = []
    for a in apps:
        rows = hist_by_app.get(a.id)
        if rows:
            for h in rows:
                events.append(
                    {"at": h.created_at, "internship": a.title, "company": a.name, "status": h.to_status, "note": h.note}
                )
        else:  # applications without a recorded history still get a minimal timeline
            events.append({"at": a.created_at, "internship": a.title, "company": a.name, "status": "PENDING", "note": None})
            if a.status != "PENDING":
                events.append(
                    {"at": a.status_changed_at, "internship": a.title, "company": a.name, "status": a.status, "note": None}
                )
    events.sort(key=lambda e: iso(e["at"]) or "", reverse=True)

    return ReportData(
        key="my-applications",
        title="My Applications",
        generated_at=now_utc(),
        params={**f.params_out(), "student_id": str(sid)} if user.role != "STUDENT" else f.params_out(),
        kpis=[kpi("Total applications", len(apps))]
        + [kpi(s.replace("_", " ").title(), c) for s, c in by_status.items() if c > 0],
        charts=[
            pie_chart("status_distribution", "donut", "Status distribution", [(s, c) for s, c in by_status.items() if c > 0])
        ],
        tables=[
            table(
                "timeline",
                "Application timeline",
                [
                    ("at", "Date", "datetime"),
                    ("internship", "Internship"),
                    ("company", "Company"),
                    ("status", "Status"),
                    ("note", "Note"),
                ],
                events[:TABLE_ROW_CAP],
            )
        ],
    )


# =========================================================================== interview-schedule
async def build_interview_schedule(session: AsyncSession, user: User, params: dict[str, Any]) -> ReportData:
    f = parse_params(params)
    sid = student_target(user, f)
    N, A, I, C = Interview, Application, Internship, Company
    now = now_utc()
    rows = (
        await session.execute(
            select(
                N.scheduled_at,
                N.duration_minutes,
                N.mode,
                N.location,
                N.meeting_link,
                N.interviewer_name,
                N.status,
                N.result,
                N.score,
                N.feedback_for_student,
                I.title,
                C.name.label("company"),
            )
            .select_from(N)
            .join(A, A.id == N.application_id)
            .join(I, I.id == A.internship_id)
            .join(C, C.id == I.company_id)
            .where(A.student_id == sid, *f.apply(N.scheduled_at), *internship_filters(f))
            .order_by(N.scheduled_at)
            .limit(TABLE_ROW_CAP)
        )
    ).all()
    upcoming = [r for r in rows if r.status in ("SCHEDULED", "RESCHEDULED") and r.scheduled_at >= now]
    completed = [r for r in rows if r.status in ("COMPLETED", "NO_SHOW")]

    return ReportData(
        key="interview-schedule",
        title="Interview Schedule",
        generated_at=now,
        params={**f.params_out(), "student_id": str(sid)} if user.role != "STUDENT" else f.params_out(),
        kpis=[
            kpi("Upcoming interviews", len(upcoming)),
            kpi("Completed interviews", len([r for r in completed if r.status == "COMPLETED"])),
        ],
        charts=[],
        tables=[
            table(
                "upcoming",
                "Upcoming interviews",
                [
                    ("when", "When", "datetime"),
                    ("internship", "Internship"),
                    ("company", "Company"),
                    ("mode", "Mode"),
                    ("where", "Location / link"),
                    ("interviewer", "Interviewer"),
                    ("duration", "Minutes", "number"),
                    ("status", "Status"),
                ],
                [
                    {
                        "when": r.scheduled_at,
                        "internship": r.title,
                        "company": r.company,
                        "mode": r.mode,
                        "where": r.meeting_link or r.location,
                        "interviewer": r.interviewer_name,
                        "duration": r.duration_minutes,
                        "status": r.status,
                    }
                    for r in upcoming
                ],
            ),
            table(
                "past_results",
                "Past interviews and results",
                [
                    ("when", "When", "datetime"),
                    ("internship", "Internship"),
                    ("company", "Company"),
                    ("status", "Status"),
                    ("result", "Result"),
                    ("score", "Score (1-5)", "number"),
                    ("feedback", "Feedback"),
                ],
                [
                    {
                        "when": r.scheduled_at,
                        "internship": r.title,
                        "company": r.company,
                        "status": r.status,
                        "result": r.result,
                        "score": r.score,
                        "feedback": r.feedback_for_student,
                    }
                    for r in sorted(completed, key=lambda r: r.scheduled_at, reverse=True)
                ],
            ),
        ],
    )


# =========================================================================== placement-status
async def build_placement_status(session: AsyncSession, user: User, params: dict[str, Any]) -> ReportData:
    f = parse_params(params)
    sid = student_target(user, f)
    A, I, C = Application, Internship, Company
    rows = (
        await session.execute(
            select(
                A.status,
                A.status_changed_at,
                A.offer_details,
                A.completed_at,
                I.title,
                I.start_date,
                I.stipend_monthly,
                I.location,
                C.name.label("company"),
            )
            .select_from(A)
            .join(I, I.id == A.internship_id)
            .join(C, C.id == I.company_id)
            .where(A.student_id == sid, *internship_filters(f))
            .order_by(A.status_changed_at.desc())
        )
    ).all()
    offers = [r for r in rows if r.status == "ACCEPTED"]
    in_process = [r for r in rows if r.status in OPEN_STATUSES]
    status = "Placed" if offers else ("In process" if in_process else "Not placed")

    def _offer(r: Any) -> dict[str, Any]:
        od = r.offer_details or {}
        return {
            "company": r.company,
            "internship": r.title,
            "stipend": num(od.get("stipend_monthly", r.stipend_monthly)),
            "start_date": od.get("start_date") or r.start_date,
            "location": od.get("joining_location") or r.location,
            "accepted_at": r.status_changed_at,
            "completed": r.completed_at is not None,
            "notes": od.get("notes"),
        }

    return ReportData(
        key="placement-status",
        title="Placement Status",
        generated_at=now_utc(),
        params={**f.params_out(), "student_id": str(sid)} if user.role != "STUDENT" else f.params_out(),
        kpis=[
            kpi("Current status", status, "text"),
            kpi("Offers", len(offers)),
            kpi("Applications in process", len(in_process)),
        ],
        charts=[],
        tables=[
            table(
                "offers",
                "Offer details",
                [
                    ("company", "Company"),
                    ("internship", "Internship"),
                    ("stipend", "Stipend (monthly)", "currency"),
                    ("start_date", "Start date", "date"),
                    ("location", "Joining location"),
                    ("accepted_at", "Accepted on", "date"),
                    ("completed", "Completed"),
                    ("notes", "Notes"),
                ],
                [_offer(r) for r in offers],
            )
        ],
    )


__all__ = ["build_my_applications", "build_interview_schedule", "build_placement_status"]
_ = func
