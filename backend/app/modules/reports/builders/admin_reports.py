"""ADMIN report builders (plan 6.11): placement-summary, application-analytics, student-performance,
company-statistics, system-activity, compliance."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Any

from sqlalchemy import Numeric, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin.models import CompliancePolicy, LoginEvent, PolicyViolation
from app.modules.applications.models import Application
from app.modules.companies.models import Company
from app.modules.documents.models import Document
from app.modules.evaluations.models import Evaluation
from app.modules.feedback.models import StudentFeedback
from app.modules.internships.models import Internship
from app.modules.reports.builders.common import (
    APPLICATION_STATUSES,
    TABLE_ROW_CAP,
    day_range,
    internship_filters,
    iso,
    kpi,
    month_key,
    month_range,
    now_utc,
    num,
    parse_params,
    pct,
    pie_chart,
    radar_chart,
    table,
    to_date,
    trunc,
    week_range,
    week_start,
    xy_chart,
)
from app.modules.reports.schemas import ReportData
from app.modules.students.models import Student
from app.modules.users.models import User

RATING_DIMENSIONS = [
    ("overall", "Overall"),
    ("company_culture", "Culture"),
    ("mentorship", "Mentorship"),
    ("technical_learning", "Technical learning"),
    ("work_environment", "Work environment"),
]


def _offer_stipend() -> Any:
    """Stipend of an accepted offer: offer_details.stipend_monthly, falling back to the internship stipend."""
    return func.coalesce(Application.offer_details["stipend_monthly"].astext.cast(Numeric), Internship.stipend_monthly)


# =========================================================================== placement-summary
async def build_placement_summary(session: AsyncSession, user: User, params: dict[str, Any]) -> ReportData:
    f = parse_params(params)
    A, I, S, U, C = Application, Internship, Student, User, Company
    conds = [A.status == "ACCEPTED", *f.apply(A.status_changed_at), *internship_filters(f)]
    stipend = _offer_stipend()

    active_students = (
        await session.execute(select(func.count(U.id)).where(U.role == "STUDENT", U.is_active.is_(True)))
    ).scalar_one()
    agg = (
        await session.execute(
            select(func.count(func.distinct(A.student_id)), func.count(A.id), func.avg(stipend))
            .select_from(A)
            .join(I, I.id == A.internship_id)
            .where(*conds)
        )
    ).one()
    placed, offers, avg_stipend = int(agg[0]), int(agg[1]), agg[2]

    by_dept = (
        await session.execute(
            select(S.department, func.count(func.distinct(A.student_id)))
            .select_from(A)
            .join(I, I.id == A.internship_id)
            .join(S, S.user_id == A.student_id)
            .where(*conds)
            .group_by(S.department)
            .order_by(func.count(func.distinct(A.student_id)).desc(), S.department)
        )
    ).all()

    month_col = trunc("month", A.status_changed_at)
    over_time = (
        await session.execute(
            select(month_col, func.count(A.id))
            .select_from(A)
            .join(I, I.id == A.internship_id)
            .where(*conds)
            .group_by(month_col)
            .order_by(month_col)
        )
    ).all()
    months: list[str] = []
    counts: dict[str, int] = {}
    if over_time:
        months = month_range(to_date(over_time[0][0]), to_date(over_time[-1][0]))
        counts = {month_key(r[0]): int(r[1]) for r in over_time}

    start = func.coalesce(A.offer_details["start_date"].astext, func.to_char(I.start_date, "YYYY-MM-DD"))
    rows = (
        await session.execute(
            select(
                U.full_name,
                U.email,
                S.department,
                S.gpa,
                C.name.label("company"),
                I.title,
                stipend.label("stipend"),
                start.label("start_date"),
                A.offer_details["joining_location"].astext.label("location"),
                A.status_changed_at,
            )
            .select_from(A)
            .join(I, I.id == A.internship_id)
            .join(C, C.id == I.company_id)
            .join(S, S.user_id == A.student_id)
            .join(U, U.id == A.student_id)
            .where(*conds)
            .order_by(A.status_changed_at.desc())
            .limit(TABLE_ROW_CAP)
        )
    ).all()

    return ReportData(
        key="placement-summary",
        title="Placement Summary",
        generated_at=now_utc(),
        params=f.params_out(),
        kpis=[
            kpi("Placement rate", pct(placed, active_students), "percent", "Students with an accepted offer / active students"),
            kpi("Students placed", placed),
            kpi("Average stipend (monthly)", num(avg_stipend), "currency", "Accepted offers; falls back to the internship stipend"),
            kpi("Total offers", offers),
        ],
        charts=[
            xy_chart(
                "placements_by_department",
                "bar",
                "Placements by department",
                [r[0] for r in by_dept],
                [("Placed students", [r[1] for r in by_dept])],
            ),
            xy_chart(
                "placements_over_time",
                "line",
                "Placements over time",
                months,
                [("Offers accepted", [counts.get(m, 0) for m in months])],
            ),
        ],
        tables=[
            table(
                "placed_students",
                "Placed students",
                [
                    ("student", "Student"),
                    ("email", "Email"),
                    ("department", "Department"),
                    ("gpa", "GPA", "number"),
                    ("company", "Company"),
                    ("internship", "Internship"),
                    ("stipend", "Stipend (monthly)", "currency"),
                    ("start_date", "Start date", "date"),
                    ("location", "Joining location"),
                    ("accepted_at", "Accepted on", "date"),
                ],
                [
                    {
                        "student": r.full_name,
                        "email": r.email,
                        "department": r.department,
                        "gpa": r.gpa,
                        "company": r.company,
                        "internship": r.title,
                        "stipend": num(r.stipend),
                        "start_date": r.start_date,
                        "location": r.location,
                        "accepted_at": r.status_changed_at,
                    }
                    for r in rows
                ],
            )
        ],
    )


# =========================================================================== application-analytics
async def build_application_analytics(session: AsyncSession, user: User, params: dict[str, Any]) -> ReportData:
    f = parse_params(params)
    A, I, C = Application, Internship, Company
    conds = [*f.apply(A.created_at), *internship_filters(f)]

    status_rows = (
        await session.execute(
            select(A.status, func.count(A.id))
            .select_from(A)
            .join(I, I.id == A.internship_id)
            .where(*conds)
            .group_by(A.status)
        )
    ).all()
    by_status = {s: 0 for s in APPLICATION_STATUSES}
    by_status.update({r[0]: int(r[1]) for r in status_rows})
    total = sum(by_status.values())

    avg_secs = (
        await session.execute(
            select(func.avg(func.extract("epoch", A.status_changed_at - A.created_at)))
            .select_from(A)
            .join(I, I.id == A.internship_id)
            .where(*conds, A.status.in_(("ACCEPTED", "REJECTED")))
        )
    ).scalar_one()
    avg_days = round(float(avg_secs) / 86400.0, 1) if avg_secs is not None else 0.0

    week_col = trunc("week", A.created_at)
    weekly = (
        await session.execute(
            select(week_col, func.count(A.id))
            .select_from(A)
            .join(I, I.id == A.internship_id)
            .where(*conds)
            .group_by(week_col)
            .order_by(week_col)
        )
    ).all()
    weeks = week_range(to_date(weekly[0][0]), to_date(weekly[-1][0])) if weekly else []
    wk_counts = {to_date(r[0]): int(r[1]) for r in weekly}

    per_internship = (
        await session.execute(
            select(
                I.title,
                C.name,
                func.count(A.id),
                *[func.count(A.id).filter(A.status == s) for s in ("PENDING", "UNDER_REVIEW", "SHORTLISTED", "INTERVIEW", "ACCEPTED", "REJECTED", "WITHDRAWN")],
            )
            .select_from(A)
            .join(I, I.id == A.internship_id)
            .join(C, C.id == I.company_id)
            .where(*conds)
            .group_by(I.id, I.title, C.name)
            .order_by(func.count(A.id).desc(), I.title)
            .limit(TABLE_ROW_CAP)
        )
    ).all()

    return ReportData(
        key="application-analytics",
        title="Application Analytics",
        generated_at=now_utc(),
        params=f.params_out(),
        kpis=[
            kpi("Total applications", total),
            kpi("Acceptance rate", pct(by_status["ACCEPTED"], total), "percent", "Accepted / all applications"),
            kpi("Avg time to decision (days)", avg_days, "number", "From submission to accepted/rejected"),
        ],
        charts=[
            pie_chart(
                "status_breakdown",
                "donut",
                "Application status breakdown",
                [(s, c) for s, c in by_status.items() if c > 0],
            ),
            xy_chart(
                "applications_per_week",
                "area",
                "Applications per week",
                [d.isoformat() for d in weeks],
                [("Applications", [wk_counts.get(d, 0) for d in weeks])],
            ),
        ],
        tables=[
            table(
                "by_internship",
                "Applications by internship",
                [
                    ("internship", "Internship"),
                    ("company", "Company"),
                    ("total", "Total", "number"),
                    ("pending", "Pending", "number"),
                    ("under_review", "Under review", "number"),
                    ("shortlisted", "Shortlisted", "number"),
                    ("interview", "Interview", "number"),
                    ("accepted", "Accepted", "number"),
                    ("rejected", "Rejected", "number"),
                    ("withdrawn", "Withdrawn", "number"),
                ],
                [
                    {
                        "internship": r[0],
                        "company": r[1],
                        "total": r[2],
                        "pending": r[3],
                        "under_review": r[4],
                        "shortlisted": r[5],
                        "interview": r[6],
                        "accepted": r[7],
                        "rejected": r[8],
                        "withdrawn": r[9],
                    }
                    for r in per_internship
                ],
            )
        ],
    )


# =========================================================================== student-performance
async def build_student_performance(session: AsyncSession, user: User, params: dict[str, Any]) -> ReportData:
    f = parse_params(params)
    A, I, S, U, E = Application, Internship, Student, User, Evaluation

    app_conds = [*f.apply(A.created_at), *internship_filters(f)]
    accepted, completed = (
        await session.execute(
            select(
                func.count(A.id).filter(A.status == "ACCEPTED"),
                func.count(A.id).filter(A.status == "ACCEPTED", A.completed_at.isnot(None)),
            )
            .select_from(A)
            .join(I, I.id == A.internship_id)
            .where(*app_conds)
        )
    ).one()

    ev_conds = [E.archived_at.is_(None), *f.apply(E.created_at), *internship_filters(f)]
    avg_eval = (
        await session.execute(
            select(func.avg(E.weighted_score))
            .select_from(E)
            .join(A, A.id == E.application_id)
            .join(I, I.id == A.internship_id)
            .where(*ev_conds)
        )
    ).scalar_one()

    avg_col = func.avg(E.weighted_score)
    top = (
        await session.execute(
            select(U.id, U.full_name, S.department, S.gpa, avg_col, func.count(E.id))
            .select_from(E)
            .join(A, A.id == E.application_id)
            .join(I, I.id == A.internship_id)
            .join(S, S.user_id == A.student_id)
            .join(U, U.id == A.student_id)
            .where(*ev_conds)
            .group_by(U.id, U.full_name, S.department, S.gpa)
            .order_by(avg_col.desc(), U.full_name)
            .limit(20)
        )
    ).all()
    ids = [r[0] for r in top]
    app_counts: dict[Any, tuple[int, int]] = {}
    if ids:
        for sid, total, acc in (
            await session.execute(
                select(A.student_id, func.count(A.id), func.count(A.id).filter(A.status == "ACCEPTED"))
                .select_from(A)
                .join(I, I.id == A.internship_id)
                .where(A.student_id.in_(ids), *app_conds)
                .group_by(A.student_id)
            )
        ).all():
            app_counts[sid] = (int(total), int(acc))

    popular = (
        await session.execute(
            select(I.title, func.count(A.id))
            .select_from(A)
            .join(I, I.id == A.internship_id)
            .where(*app_conds)
            .group_by(I.id, I.title)
            .order_by(func.count(A.id).desc(), I.title)
            .limit(10)
        )
    ).all()

    return ReportData(
        key="student-performance",
        title="Student Performance",
        generated_at=now_utc(),
        params=f.params_out(),
        kpis=[
            kpi("Completion rate", pct(completed, accepted), "percent", "Completed internships / accepted offers"),
            kpi("Avg evaluation score", num(avg_eval, 1), "number", "Weighted score out of 100"),
        ],
        charts=[
            xy_chart(
                "top_students",
                "bar",
                "Top performing students (avg weighted score)",
                [r[1] for r in top[:10]],
                [("Avg score", [num(r[4], 1) for r in top[:10]])],
            ),
            xy_chart(
                "popular_internships",
                "bar",
                "Most popular internships (applications)",
                [r[0] for r in popular],
                [("Applications", [r[1] for r in popular])],
            ),
        ],
        tables=[
            table(
                "top_students",
                "Top 20 students",
                [
                    ("rank", "Rank", "number"),
                    ("student", "Student"),
                    ("department", "Department"),
                    ("gpa", "GPA", "number"),
                    ("avg_score", "Avg evaluation score", "number"),
                    ("evaluations", "Evaluations", "number"),
                    ("applications", "Applications", "number"),
                    ("accepted", "Accepted", "number"),
                ],
                [
                    {
                        "rank": i + 1,
                        "student": r[1],
                        "department": r[2],
                        "gpa": r[3],
                        "avg_score": num(r[4], 1),
                        "evaluations": r[5],
                        "applications": app_counts.get(r[0], (0, 0))[0],
                        "accepted": app_counts.get(r[0], (0, 0))[1],
                    }
                    for i, r in enumerate(top)
                ],
            )
        ],
    )


# =========================================================================== company-statistics
async def build_company_statistics(session: AsyncSession, user: User, params: dict[str, Any]) -> ReportData:
    f = parse_params(params)
    C, I, A, SF = Company, Internship, Application, StudentFeedback

    comp_conds = [C.archived_at.is_(None)]
    if f.company_id:
        comp_conds.append(C.id == f.company_id)
    companies = (
        await session.execute(
            select(C.id, C.name, C.industry, C.location, C.status).where(*comp_conds).order_by(C.name)
        )
    ).all()
    active = sum(1 for c in companies if c.status == "ACTIVE")

    int_counts = dict(
        (await session.execute(select(I.company_id, func.count(I.id)).where(I.archived_at.is_(None), *f.apply(I.created_at)).group_by(I.company_id))).all()
    )
    app_counts = dict(
        (
            await session.execute(
                select(I.company_id, func.count(A.id))
                .select_from(A)
                .join(I, I.id == A.internship_id)
                .where(*f.apply(A.created_at))
                .group_by(I.company_id)
            )
        ).all()
    )
    fb_conds = [*f.apply(SF.created_at)]
    dims = [func.avg(getattr(SF, k)) for k, _ in RATING_DIMENSIONS]
    fb_rows = (
        await session.execute(
            select(SF.company_id, func.count(SF.id), *dims).where(*fb_conds).group_by(SF.company_id)
        )
    ).all()
    fb = {r[0]: r for r in fb_rows}
    latest_rows = (
        await session.execute(
            select(SF.company_id, SF.comments)
            .where(SF.comments.isnot(None), *fb_conds)
            .order_by(SF.company_id, SF.created_at.desc())
            .distinct(SF.company_id)
        )
    ).all()
    latest = {r[0]: r[1] for r in latest_rows}
    overall = (
        await session.execute(select(func.count(SF.id), *dims).where(*fb_conds))
    ).one()
    fb_total = int(overall[0])

    stats = []
    for c in companies:
        r = fb.get(c.id)
        stats.append(
            {
                "id": c.id,
                "name": c.name,
                "industry": c.industry,
                "location": c.location,
                "status": c.status,
                "internships": int(int_counts.get(c.id, 0)),
                "applications": int(app_counts.get(c.id, 0)),
                "feedback_count": int(r[1]) if r else 0,
                "avg_rating": num(r[2], 2) if r else None,
                "dims": [num(v, 2) for v in r[2:]] if r else [0] * len(RATING_DIMENSIONS),
                "latest_comment": latest.get(c.id),
            }
        )
    most_active = sorted(stats, key=lambda s: (-(s["internships"] + s["applications"]), s["name"]))[:8]
    top_rated = sorted((s for s in stats if s["feedback_count"]), key=lambda s: (-s["feedback_count"], s["name"]))[:3]
    radar_series = [("All companies", [num(v, 2) for v in overall[1:]])]
    radar_series += [(s["name"], s["dims"]) for s in top_rated]

    return ReportData(
        key="company-statistics",
        title="Company Statistics",
        generated_at=now_utc(),
        params=f.params_out(),
        kpis=[
            kpi("Active companies", active),
            kpi("Average rating", num(overall[1], 2) if fb_total else 0, "number", "Mean overall student rating (1-5)"),
            kpi("Student feedback count", fb_total),
        ],
        charts=[
            xy_chart(
                "most_active_companies",
                "bar",
                "Most active companies",
                [s["name"] for s in most_active],
                [
                    ("Internships", [s["internships"] for s in most_active]),
                    ("Applications", [s["applications"] for s in most_active]),
                ],
            ),
            radar_chart(
                "rating_radar",
                "Company rating profile",
                [(label, 5) for _, label in RATING_DIMENSIONS],
                radar_series,
            ),
        ],
        tables=[
            table(
                "companies",
                "Companies and student feedback summary",
                [
                    ("company", "Company"),
                    ("industry", "Industry"),
                    ("location", "Location"),
                    ("status", "Status"),
                    ("internships", "Internships", "number"),
                    ("applications", "Applications", "number"),
                    ("feedback_count", "Feedback count", "number"),
                    ("avg_rating", "Avg overall rating", "number"),
                    ("latest_comment", "Latest comment"),
                ],
                [
                    {
                        "company": s["name"],
                        "industry": s["industry"],
                        "location": s["location"],
                        "status": s["status"],
                        "internships": s["internships"],
                        "applications": s["applications"],
                        "feedback_count": s["feedback_count"],
                        "avg_rating": s["avg_rating"],
                        "latest_comment": s["latest_comment"],
                    }
                    for s in stats[:TABLE_ROW_CAP]
                ],
            )
        ],
    )


# =========================================================================== system-activity
async def build_system_activity(session: AsyncSession, user: User, params: dict[str, Any]) -> ReportData:
    f = parse_params(params)
    now = now_utc()
    if f.date_to is None and f.date_from is None:
        d_to = now.date()
        d_from = d_to - timedelta(days=29)
    else:
        d_to = f.raw_to or now.date()
        d_from = f.raw_from or (d_to - timedelta(days=29))
    if (d_to - d_from).days > 366:
        d_from = d_to - timedelta(days=366)
    from datetime import UTC, datetime

    start = datetime(d_from.year, d_from.month, d_from.day, tzinfo=UTC)
    end = datetime(d_to.year, d_to.month, d_to.day, tzinfo=UTC) + timedelta(days=1)
    U, L, D = User, LoginEvent, Document

    regs = (await session.execute(select(func.count(U.id)).where(U.created_at >= start, U.created_at < end))).scalar_one()
    login_ok = (
        await session.execute(select(func.count(L.id)).where(L.success.is_(True), L.created_at >= start, L.created_at < end))
    ).scalar_one()
    seven = now - timedelta(days=7)
    active_login = select(L.user_id.label("uid")).where(L.success.is_(True), L.created_at >= seven, L.user_id.isnot(None))
    active_seen = select(U.id.label("uid")).where(U.last_login_at >= seven)
    union = active_login.union(active_seen).subquery()
    active_7d = (await session.execute(select(func.count()).select_from(union))).scalar_one()

    doc_rows = (
        await session.execute(
            select(D.bucket, func.count(D.id), func.coalesce(func.sum(D.size_bytes), 0))
            .where(D.deleted_at.is_(None), D.status == "UPLOADED")
            .group_by(D.bucket)
            .order_by(D.bucket)
        )
    ).all()
    doc_count = sum(int(r[1]) for r in doc_rows)
    storage_mb = round(sum(int(r[2]) for r in doc_rows) / (1024 * 1024), 2)

    day_col = trunc("day", U.created_at)
    reg_rows = (
        await session.execute(
            select(day_col, U.role, func.count(U.id))
            .where(U.created_at >= start, U.created_at < end)
            .group_by(day_col, U.role)
        )
    ).all()
    reg_map: dict[tuple, int] = {(to_date(r[0]), r[1]): int(r[2]) for r in reg_rows}
    days = day_range(d_from, d_to)
    roles = ["STUDENT", "FACULTY", "COMPANY", "ADMIN"]

    lday = trunc("day", L.created_at)
    login_rows = (
        await session.execute(
            select(lday, L.success, func.count(L.id))
            .where(L.created_at >= start, L.created_at < end)
            .group_by(lday, L.success)
        )
    ).all()
    login_map = {(to_date(r[0]), bool(r[1])): int(r[2]) for r in login_rows}

    return ReportData(
        key="system-activity",
        title="System Activity",
        generated_at=now,
        params={"from": d_from.isoformat(), "to": d_to.isoformat()},
        kpis=[
            kpi("Registrations (period)", regs),
            kpi("Successful logins (period)", login_ok),
            kpi("Active users (7d)", active_7d),
            kpi("Storage used (MB)", storage_mb, "number"),
            kpi("Documents", doc_count),
        ],
        charts=[
            xy_chart(
                "registrations_per_day",
                "line",
                "Registrations per day by role",
                [d.isoformat() for d in days],
                [(r.title(), [reg_map.get((d, r), 0) for d in days]) for r in roles],
            ),
            xy_chart(
                "login_trends",
                "line",
                "Login trends",
                [d.isoformat() for d in days],
                [
                    ("Successful", [login_map.get((d, True), 0) for d in days]),
                    ("Failed", [login_map.get((d, False), 0) for d in days]),
                ],
            ),
            pie_chart(
                "storage_by_bucket",
                "pie",
                "Storage by bucket (MB)",
                [(r[0], round(int(r[2]) / (1024 * 1024), 3)) for r in doc_rows],
            ),
        ],
        tables=[],
    )


# =========================================================================== compliance
_USER_DOC_KINDS = ("RESUME", "COVER_LETTER", "TRANSCRIPT", "OFFER_LETTER", "OTHER")


async def build_compliance(session: AsyncSession, user: User, params: dict[str, Any]) -> ReportData:
    f = parse_params(params)
    P, V, D, U = CompliancePolicy, PolicyViolation, Document, User
    now = now_utc()

    status_counts = dict(
        (await session.execute(select(V.status, func.count(V.id)).where(*f.apply(V.created_at)).group_by(V.status))).all()
    )
    open_count = int(status_counts.get("OPEN", 0))
    resolved = int(status_counts.get("RESOLVED", 0))

    doc_conds = [D.deleted_at.is_(None), D.status == "UPLOADED", D.kind.in_(_USER_DOC_KINDS), *f.apply(D.created_at)]
    ver = dict(
        (await session.execute(select(D.verification_status, func.count(D.id)).where(*doc_conds).group_by(D.verification_status))).all()
    )
    ver_total = sum(int(v) for v in ver.values())
    pending_docs = int(ver.get("PENDING", 0))

    by_policy = (
        await session.execute(
            select(P.name, func.count(V.id))
            .select_from(V)
            .join(P, P.id == V.policy_id)
            .where(V.status == "OPEN", *f.apply(V.created_at))
            .group_by(P.id, P.name)
            .order_by(func.count(V.id).desc(), P.name)
        )
    ).all()

    open_rows = (
        await session.execute(
            select(P.code, P.name, P.severity, V.entity_type, V.entity_id, V.details, V.created_at)
            .select_from(V)
            .join(P, P.id == V.policy_id)
            .where(V.status == "OPEN", *f.apply(V.created_at))
            .order_by(V.created_at.desc())
            .limit(TABLE_ROW_CAP)
        )
    ).all()
    doc_rows = (
        await session.execute(
            select(D.filename, D.kind, U.full_name, U.email, D.created_at)
            .select_from(D)
            .join(U, U.id == D.owner_id)
            .where(*doc_conds, D.verification_status == "PENDING")
            .order_by(D.created_at)
            .limit(TABLE_ROW_CAP)
        )
    ).all()

    def _details(d: Any) -> str:
        if not isinstance(d, dict):
            return ""
        return "; ".join(f"{k}: {v}" for k, v in list(d.items())[:4])[:200]

    return ReportData(
        key="compliance",
        title="Compliance Report",
        generated_at=now,
        params=f.params_out(),
        kpis=[
            kpi("Open violations", open_count),
            kpi("Resolved violations", resolved),
            kpi("Documents pending verification", pending_docs),
            kpi("Verified documents", pct(int(ver.get("VERIFIED", 0)), ver_total), "percent", "Verified / uploaded documents"),
        ],
        charts=[
            xy_chart(
                "violations_by_policy",
                "bar",
                "Open violations by policy",
                [r[0] for r in by_policy],
                [("Open violations", [r[1] for r in by_policy])],
            ),
            pie_chart(
                "document_verification",
                "donut",
                "Document verification status",
                [(s.title(), int(ver.get(s, 0))) for s in ("VERIFIED", "PENDING", "REJECTED") if ver.get(s, 0)],
            ),
        ],
        tables=[
            table(
                "open_violations",
                "Open violations",
                [
                    ("policy", "Policy"),
                    ("severity", "Severity"),
                    ("entity_type", "Entity"),
                    ("entity_id", "Entity ID"),
                    ("details", "Details"),
                    ("detected_at", "Detected", "datetime"),
                ],
                [
                    {
                        "policy": r.name,
                        "severity": r.severity,
                        "entity_type": r.entity_type,
                        "entity_id": r.entity_id,
                        "details": _details(r.details),
                        "detected_at": r.created_at,
                    }
                    for r in open_rows
                ],
            ),
            table(
                "pending_documents",
                "Documents pending verification",
                [
                    ("filename", "File"),
                    ("kind", "Kind"),
                    ("owner", "Owner"),
                    ("email", "Email"),
                    ("uploaded_at", "Uploaded", "datetime"),
                    ("age_days", "Age (days)", "number"),
                ],
                [
                    {
                        "filename": r.filename,
                        "kind": r.kind,
                        "owner": r.full_name,
                        "email": r.email,
                        "uploaded_at": r.created_at,
                        "age_days": (now - r.created_at).days,
                    }
                    for r in doc_rows
                ],
            ),
        ],
    )


__all__ = [
    "build_placement_summary",
    "build_application_analytics",
    "build_student_performance",
    "build_company_statistics",
    "build_system_activity",
    "build_compliance",
]

# silence unused import warnings for helpers kept for readability
_ = (and_, defaultdict, iso, week_start)
