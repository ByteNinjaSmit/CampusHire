"""Import every module's models so Base.metadata is complete (Alembic, tests, seed)."""

from app.core.base import Base
from app.modules.admin.models import AuditLog, CompliancePolicy, Job, LoginEvent, PolicyViolation
from app.modules.applications.models import Application, ApplicationStatusHistory
from app.modules.auth.models import RefreshToken, UserToken
from app.modules.companies.models import Company, CompanyMember
from app.modules.documents.models import Document
from app.modules.evaluations.models import Evaluation, EvaluationCriterion, EvaluationForm, EvaluationScore
from app.modules.faculty.models import Faculty
from app.modules.feedback.models import (
    CompanyFeedback,
    FacultyFeedback,
    FeedbackActionItem,
    StudentFeedback,
    SystemFeedback,
)
from app.modules.internships.models import Internship, SavedInternship
from app.modules.interviews.models import Interview
from app.modules.notifications.models import Notification
from app.modules.students.models import Student
from app.modules.users.models import User

__all__ = [
    "Base",
    "AuditLog",
    "CompliancePolicy",
    "Job",
    "LoginEvent",
    "PolicyViolation",
    "Application",
    "ApplicationStatusHistory",
    "RefreshToken",
    "UserToken",
    "Company",
    "CompanyMember",
    "Document",
    "Evaluation",
    "EvaluationCriterion",
    "EvaluationForm",
    "EvaluationScore",
    "Faculty",
    "CompanyFeedback",
    "FacultyFeedback",
    "FeedbackActionItem",
    "StudentFeedback",
    "SystemFeedback",
    "Internship",
    "SavedInternship",
    "Interview",
    "Notification",
    "Student",
    "User",
]
