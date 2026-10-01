"""FACULTY / COMPANY report builders, scoped to the caller's own internships (ADMIN: unscoped).

posted-internships, application-review, student-evaluations, interview-statistics (plan 6.11).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import Integer, case, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.applications.models import Application, ApplicationStatusHistory
from app.modules.companies.models import Company
from app.modules.evaluations.models import Evaluation, EvaluationCriterion, EvaluationScore
from app.modules.feedback.models import CompanyFeedback
from app.modules.interviews.models import Interview
from app.modules.internships.models import Internship
from app.modules.reports.builders.common import (
    TABLE_ROW_CAP,
    internship_scope,
    kpi,
    now_utc,
    num,
    parse_params,
    pct,
    pie_chart,
    table,
    to_date,
    trunc,
    week_range,
    xy_chart,
)
from app.modules.reports.schemas import ReportData
from app.modules.students.models import Student
from app.modules.users.models import User

SHORTLISTED_OR_BEYOND = ("SHORTLISTED", "INTERVIEW", "ACCEPTED")


# =========================================================================== posted-internships
async def build_posted_internships(session: AsyncSession, user: User, params: dict[str, Any]) -> ReportData:
    f = parse_params(params)
    I, A, C = Internship, Application, Company
    scope = await internship_scope(session, user, f)
    rows = (
        await session.execute(
            select(
                I.id,
                I.title,
                C.name.label("company"),
                I.domain,
                I.status,
                I.application_deadline,
                func.count(A.id).label("apps"),
                func.count(A.id).filter(A.status.in_(SHORTLISTED_OR_BEYOND)).label("shortlisted"),
                func.count(A.id).filter(A.status == "ACCEPTED").label("accepted"),
            )
            .select_from(I)
            .join(C, C.id == I.company_id)
            .outerjoin(A, A.internship_id == I.id)
            .where(*scope, I.archived_at.is_(None), *f.apply(I.created_at))
            .group_by(I.id, C.name)
            .order_by(I.created_at.desc(), I.title)
            .limit(TABLE_ROW_CAP)
        )
    ).all()
    postings = len(rows)
    total_apps = sum(int(r.apps) for r in rows)
    status_counts: dict[str, int] = {}
    for r in rows:
        status_counts[r.status] = status_counts.get(r.status, 0) + 1
    top = sorted(rows, key=lambda r: (-int(r.apps), r.title))[:10]

    return ReportData(
        key="posted-internships",
        title="Posted Internships",
        generated_at=now_utc(),
        params=f.params_out(),
        kpis=[
            kpi("Postings", postings),
            kpi("Total applications", total_apps),
            kpi("Avg applications per internship", round(total_apps / postings, 2) if postings else 0),
        ],
        charts=[
            pie_chart("status_breakdown", "donut", "Postings by status", list(status_counts.items())),
            xy_chart(
                "applications_per_internship",
                "bar",
                "Applications per internship",
                [r.title for r in top],
                [("Applications", [int(r.apps) for r in top])],
            ),
        ],
        tables=[
            table(
                "postings",
                "Postings",
                [
                    ("title", "Internship"),
                    ("company", "Company"),
                    ("domain", "Domain"),
                    ("status", "Status"),
                    ("deadline", "Deadline", "datetime"),
                    ("applications", "Applications", "number"),
                    ("shortlisted", "Shortlisted+", "number"),
                    ("accepted", "Accepted", "number"),
                ],
                [
                    {
                        "title": r.title,
                        "company": r.company,
                        "domain": r.domain,
                        "status": r.status,
                        "deadline": r.application_deadline,
                        "applications": int(r.apps),
                        "shortlisted": int(r.shortlisted),
                        "accepted": int(r.accepted),
                    }
                    for r in rows
                ],
            )
        ],
    )


# =========================================================================== application-review
async def build_application_review(session: AsyncSession, user: User, params: dict[str, Any]) -> ReportData:
    f = parse_params(params)
    I, A, C, H = Internship, Application, Company, ApplicationStatusHistory
    scope = await internship_scope(session, user, f)

    def ever(status: str) -> Any:
        return exists().where(H.application_id == A.id, H.to_status == status)

    reached_shortlist = or_(A.status.in_(SHORTLISTED_OR_BEYOND), ever("SHORTLISTED"))
    reached_interview = or_(
        A.status == "INTERVIEW",
        ever("INTERVIEW"),
        exists().where(Interview.application_id == A.id, Interview.status != "CANCELLED"),
    )
    base = [*scope, *f.apply(A.created_at)]
    agg = (
        await session.execute(
            select(
                func.count(A.id),
                func.count(A.id).filter(A.status == "PENDING"),
                func.count(A.id).filter(A.status == "WITHDRAWN"),
                func.count(A.id).filter(reached_shortlist),
                func.count(A.id).filter(reached_interview),
                func.count(A.id).filter(A.status == "ACCEPTED"),
            )
            .select_from(A)
            .join(I, I.id == A.internship_id)
            .where(*base)
        )
    ).one()
    total, pending, withdrawn, shortlisted, interviewed, accepted = (int(v) for v in agg)
    reviewed = total - pending - withdrawn

    per_internship = (
        await session.execute(
            select(
                I.title,
                C.name,
                func.count(A.id),
                func.count(A.id).filter(A.status == "PENDING"),
                func.count(A.id).filter(A.status.in_(SHORTLISTED_OR_BEYOND)),
                func.count(A.id).filter(A.status == "REJECTED"),
                func.count(A.id).filter(A.status == "ACCEPTED"),
            )
            .select_from(A)
            .join(I, I.id == A.internship_id)
            .join(C, C.id == I.company_id)
            .where(*base)
            .group_by(I.id, I.title, C.name)
            .order_by(func.count(A.id).desc(), I.title)
            .limit(TABLE_ROW_CAP)
        )
    ).all()

    return ReportData(
        key="application-review",
        title="Application Review",
        generated_at=now_utc(),
        params=f.params_out(),
        kpis=[
            kpi("Reviewed", reviewed, "number", "Applications no longer PENDING (withdrawn excluded)"),
            kpi("Pending", pending),
            kpi("Shortlisting rate", pct(shortlisted, total), "percent", "Applications that reached SHORTLISTED / all applications"),
        ],
        charts=[
            pie_chart("reviewed_vs_pending", "pie", "Reviewed vs pending", [("Reviewed", reviewed), ("Pending", pending)]),
            xy_chart(
                "funnel",
                "bar",
                "Review funnel",
                ["Received", "Shortlisted", "Interviewed", "Accepted"],
                [("Applications", [total, shortlisted, interviewed, accepted])],
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
                    ("shortlisted", "Shortlisted+", "number"),
                    ("rejected", "Rejected", "number"),
                    ("accepted", "Accepted", "number"),
                ],
                [
                    {
                        "internship": r[0],
                        "company": r[1],
                        "total": r[2],
                        "pending": r[3],
                        "shortlisted": r[4],
                        "rejected": r[5],
                        "accepted": r[6],
                    }
                    for r in per_internship
                ],
            )
        ],
    )


# =========================================================================== student-evaluations
_BUCKETS = ["0-20", "20-40", "40-60", "60-80", "80-100"]


async def build_student_evaluations(session: AsyncSession, user: User, params: dict[str, Any]) -> ReportData:
    f = parse_params(params)
    E, A, I, S, U = Evaluation, Application, Internship, Student, User
    scope = await internship_scope(session, user, f)
    conds = [*scope, E.archived_at.is_(None), *f.apply(E.created_at)]

    agg = (
        await session.execute(
            select(func.count(func.distinct(A.student_id)), func.avg(E.weighted_score), func.count(E.id))
            .select_from(E)
            .join(A, A.id == E.application_id)
            .join(I, I.id == A.internship_id)
            .where(*conds)
        )
    ).one()
    evaluated, avg_score = int(agg[0]), agg[1]

    crit = (
        await session.execute(
            select(
                EvaluationCriterion.name,
                func.avg(EvaluationScore.score * 100.0 / EvaluationCriterion.max_score),
            )
            .select_from(EvaluationScore)
            .join(EvaluationCriterion, EvaluationCriterion.id == EvaluationScore.criterion_id)
            .join(E, E.id == EvaluationScore.evaluation_id)
            .join(A, A.id == E.application_id)
            .join(I, I.id == A.internship_id)
            .where(*conds)
            .group_by(EvaluationCriterion.name)
            .order_by(EvaluationCriterion.name)
        )
    ).all()

    bucket = func.least(func.floor(E.weighted_score / 20), 4).cast(Integer)
    dist_rows = (
        await session.execute(
            select(bucket, func.count(E.id))
            .select_from(E)
            .join(A, A.id == E.application_id)
            .join(I, I.id == A.internship_id)
            .where(*conds)
            .group_by(bucket)
        )
    ).all()
    dist = {int(r[0]): int(r[1]) for r in dist_rows}

    ev_rows = (
        await session.execute(
            select(
                U.full_name,
                S.department,
                I.title,
                E.weighted_score,
                E.recommendation,
                E.created_at,
                E.overall_comments,
            )
            .select_from(E)
            .join(A, A.id == E.application_id)
            .join(I, I.id == A.internship_id)
            .join(S, S.user_id == A.student_id)
            .join(U, U.id == A.student_id)
            .where(*conds)
            .order_by(E.created_at.desc())
            .limit(TABLE_ROW_CAP)
        )
    ).all()

    CF = CompanyFeedback
    fb_avg = (
        CF.technical_skills + CF.soft_skills + CF.punctuality + CF.responsibility + CF.teamwork + CF.learning_ability
    ) / 6.0
    fb_rows = (
        await session.execute(
            select(U.full_name, I.title, fb_avg, CF.hire_likelihood, CF.strengths, CF.improvements, CF.created_at)
            .select_from(CF)
            .join(A, A.id == CF.application_id)
            .join(I, I.id == A.internship_id)
            .join(U, U.id == A.student_id)
            .where(*scope, *f.apply(CF.created_at))
            .order_by(CF.created_at.desc())
            .limit(TABLE_ROW_CAP)
        )
    ).all()

    return ReportData(
        key="student-evaluations",
        title="Student Evaluations",
        generated_at=now_utc(),
        params=f.params_out(),
        kpis=[
            kpi("Students evaluated", evaluated),
            kpi("Avg weighted score", num(avg_score, 1), "number", "Out of 100"),
            *[kpi(f"Avg {name}", num(val, 1), "percent", "Average score as % of the criterion maximum") for name, val in crit],
        ],
        charts=[
            xy_chart(
                "score_distribution",
                "bar",
                "Score distribution",
                _BUCKETS,
                [("Evaluations", [dist.get(i, 0) for i in range(5)])],
            )
        ],
        tables=[
            table(
                "evaluations",
                "Evaluations",
                [
                    ("student", "Student"),
                    ("department", "Department"),
                    ("internship", "Internship"),
                    ("score", "Weighted score", "number"),
                    ("recommendation", "Recommendation"),
                    ("evaluated_at", "Date", "date"),
                    ("comments", "Comments"),
                ],
                [
                    {
                        "student": r.full_name,
                        "department": r.department,
                        "internship": r.title,
                        "score": num(r.weighted_score, 1),
                        "recommendation": r.recommendation,
                        "evaluated_at": r.created_at,
                        "comments": r.overall_comments,
                    }
                    for r in ev_rows
                ],
            ),
            table(
                "feedback_summary",
                "Company feedback summary",
                [
                    ("student", "Student"),
                    ("internship", "Internship"),
                    ("average", "Avg rating (1-5)", "number"),
                    ("hire_likelihood", "Hire likelihood (1-5)", "number"),
                    ("strengths", "Strengths"),
                    ("improvements", "Improvements"),
                    ("at", "Date", "date"),
                ],
                [
                    {
                        "student": r[0],
                        "internship": r[1],
                        "average": num(r[2], 2),
                        "hire_likelihood": r[3],
                        "strengths": r[4],
                        "improvements": r[5],
                        "at": r[6],
                    }
                    for r in fb_rows
                ],
            ),
        ],
    )


# =========================================================================== interview-statistics
async def build_interview_statistics(session: AsyncSession, user: User, params: dict[str, Any]) -> ReportData:
    f = parse_params(params)
    N, A, I, U = Interview, Application, Internship, User
    scope = await internship_scope(session, user, f)
    conds = [*scope, *f.apply(N.scheduled_at)]
    now = now_utc()

    grp = (
        await session.execute(
            select(N.status, N.result, func.count(N.id))
            .select_from(N)
            .join(A, A.id == N.application_id)
            .join(I, I.id == A.internship_id)
            .where(*conds)
            .group_by(N.status, N.result)
        )
    ).all()
    cancelled = sum(int(c) for s, _, c in grp if s == "CANCELLED")
    scheduled = sum(int(c) for s, _, c in grp if s != "CANCELLED")
    completed = sum(int(c) for s, _, c in grp if s == "COMPLETED")
    no_show = sum(int(c) for s, _, c in grp if s == "NO_SHOW")
    passed = sum(int(c) for s, r, c in grp if s == "COMPLETED" and r == "PASS")
    failed = sum(int(c) for s, r, c in grp if s == "COMPLETED" and r == "FAIL")
    on_hold = sum(int(c) for s, r, c in grp if s == "COMPLETED" and r == "ON_HOLD")
    awaiting = sum(int(c) for s, _, c in grp if s in ("SCHEDULED", "RESCHEDULED"))
    completed_other = completed - passed - failed - on_hold  # completed without a recorded result

    week_col = trunc("week", N.scheduled_at)
    weekly = (
        await session.execute(
            select(week_col, func.count(N.id))
            .select_from(N)
            .join(A, A.id == N.application_id)
            .join(I, I.id == A.internship_id)
            .where(*conds, N.status != "CANCELLED")
            .group_by(week_col)
            .order_by(week_col)
        )
    ).all()
    weeks = week_range(to_date(weekly[0][0]), to_date(weekly[-1][0])) if weekly else []
    wk = {to_date(r[0]): int(r[1]) for r in weekly}

    upcoming = (
        await session.execute(
            select(N.scheduled_at, U.full_name, I.title, N.mode, N.interviewer_name, N.status, N.duration_minutes)
            .select_from(N)
            .join(A, A.id == N.application_id)
            .join(I, I.id == A.internship_id)
            .join(U, U.id == A.student_id)
            .where(*scope, N.status.in_(("SCHEDULED", "RESCHEDULED")), N.scheduled_at >= now)
            .order_by(N.scheduled_at)
            .limit(TABLE_ROW_CAP)
        )
    ).all()

    result_data = [
        ("Pass", passed),
        ("Fail", failed),
        ("On hold", on_hold),
        ("No-show", no_show),
        ("Awaiting", awaiting),
        ("No result recorded", completed_other),
    ]
    return ReportData(
        key="interview-statistics",
        title="Interview Statistics",
        generated_at=now,
        params=f.params_out(),
        kpis=[
            kpi("Interviews scheduled", scheduled, "number", f"Excluding {cancelled} cancelled"),
            kpi("Completed", completed),
            kpi("Success rate", pct(passed, completed), "percent", "PASS / COMPLETED"),
            kpi("No-show rate", pct(no_show, scheduled), "percent", "NO_SHOW / scheduled"),
        ],
        charts=[
            xy_chart(
                "interviews_per_week",
                "bar",
                "Interviews per week",
                [d.isoformat() for d in weeks],
                [("Interviews", [wk.get(d, 0) for d in weeks])],
            ),
            pie_chart("results", "donut", "Interview results", [(n, v) for n, v in result_data if v > 0]),
        ],
        tables=[
            table(
                "upcoming",
                "Upcoming interviews",
                [
                    ("scheduled_at", "When", "datetime"),
                    ("student", "Student"),
                    ("internship", "Internship"),
                    ("mode", "Mode"),
                    ("interviewer", "Interviewer"),
                    ("duration", "Minutes", "number"),
                    ("status", "Status"),
                ],
                [
                    {
                        "scheduled_at": r.scheduled_at,
                        "student": r.full_name,
                        "internship": r.title,
                        "mode": r.mode,
                        "interviewer": r.interviewer_name,
                        "duration": r.duration_minutes,
                        "status": r.status,
                    }
                    for r in upcoming
                ],
            )
        ],
    )


__all__ = [
    "build_posted_internships",
    "build_application_review",
    "build_student_evaluations",
    "build_interview_statistics",
]
_ = (case, timedelta)
