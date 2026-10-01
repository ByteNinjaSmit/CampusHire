"""Report registry: key -> (meta, allowed roles, builder). Keys use hyphens on the wire, builders use underscores."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reports.builders.admin_reports import (
    build_application_analytics,
    build_company_statistics,
    build_compliance,
    build_placement_summary,
    build_student_performance,
    build_system_activity,
)
from app.modules.reports.builders.staff_reports import (
    build_application_review,
    build_interview_statistics,
    build_posted_internships,
    build_student_evaluations,
)
from app.modules.reports.builders.student_reports import (
    build_interview_schedule,
    build_my_applications,
    build_placement_status,
)
from app.modules.reports.schemas import ReportData, ReportMeta
from app.modules.users.models import User

Builder = Callable[[AsyncSession, User, dict[str, Any]], Awaitable[ReportData]]

_PERIOD = ["from", "to"]
_STAFF_PARAMS = ["from", "to", "internship_id", "company_id"]


@dataclass(frozen=True)
class ReportDef:
    meta: ReportMeta
    roles: frozenset[str]
    builder: Builder
    listed_for: frozenset[str]  # roles for which GET /reports lists it (ADMIN may still call every key)


def _def(
    key: str,
    title: str,
    description: str,
    params: list[str],
    roles: set[str],
    builder: Builder,
    listed_for: set[str] | None = None,
) -> ReportDef:
    return ReportDef(
        meta=ReportMeta(key=key, title=title, description=description, formats=["pdf", "xlsx"], params=params),  # type: ignore[arg-type]
        roles=frozenset(roles),
        builder=builder,
        listed_for=frozenset(listed_for if listed_for is not None else roles),
    )


_ADMIN = {"ADMIN"}
_STAFF = {"FACULTY", "COMPANY", "ADMIN"}
_STUDENT = {"STUDENT", "ADMIN"}

REPORTS: dict[str, ReportDef] = {
    d.meta.key: d
    for d in [
        _def("placement-summary", "Placement Summary", "Placement rate, offers, stipends and placed students.",
             ["from", "to", "company_id", "internship_id"], _ADMIN, build_placement_summary),
        _def("application-analytics", "Application Analytics", "Application volume, status breakdown and decision times.",
             ["from", "to", "company_id", "internship_id"], _ADMIN, build_application_analytics),
        _def("student-performance", "Student Performance", "Completion rate, evaluation scores and popular internships.",
             ["from", "to", "company_id", "internship_id"], _ADMIN, build_student_performance),
        _def("company-statistics", "Company Statistics", "Company activity, ratings and student feedback summary.",
             ["from", "to", "company_id"], _ADMIN, build_company_statistics),
        _def("system-activity", "System Activity", "Registrations, logins, active users and storage.",
             _PERIOD, _ADMIN, build_system_activity),
        _def("compliance", "Compliance", "Policy violations and document verification status.",
             _PERIOD, _ADMIN, build_compliance),
        _def("posted-internships", "Posted Internships", "Your postings, their status and applications received.",
             _STAFF_PARAMS, _STAFF, build_posted_internships, {"FACULTY", "COMPANY"}),
        _def("application-review", "Application Review", "Review progress and the shortlisting funnel for your internships.",
             _STAFF_PARAMS, _STAFF, build_application_review, {"FACULTY", "COMPANY"}),
        _def("student-evaluations", "Student Evaluations", "Evaluation scores per criterion and company feedback on students.",
             _STAFF_PARAMS, _STAFF, build_student_evaluations, {"FACULTY", "COMPANY"}),
        _def("interview-statistics", "Interview Statistics", "Interview volume, outcomes and upcoming schedule.",
             _STAFF_PARAMS, _STAFF, build_interview_statistics, {"FACULTY", "COMPANY"}),
        _def("my-applications", "My Applications", "All your applications with their status timeline.",
             _PERIOD, _STUDENT, build_my_applications, {"STUDENT"}),
        _def("interview-schedule", "Interview Schedule", "Upcoming interviews and past results with feedback.",
             _PERIOD, _STUDENT, build_interview_schedule, {"STUDENT"}),
        _def("placement-status", "Placement Status", "Your current placement status and offer details.",
             [], _STUDENT, build_placement_status, {"STUDENT"}),
    ]
}

__all__ = [
    "REPORTS",
    "ReportDef",
    "build_placement_summary",
    "build_application_analytics",
    "build_student_performance",
    "build_company_statistics",
    "build_system_activity",
    "build_compliance",
    "build_posted_internships",
    "build_application_review",
    "build_student_evaluations",
    "build_interview_statistics",
    "build_my_applications",
    "build_interview_schedule",
    "build_placement_status",
]
