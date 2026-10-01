"""Static demo data for ``python -m app.seed`` (plan 7.4). Credentials are documented in the README."""

from dataclasses import dataclass, field

ADMIN_EMAIL = "admin@campushire.dev"

PASSWORDS = {
    "ADMIN": "Admin@12345",
    "FACULTY": "Faculty@12345",
    "STUDENT": "Student@12345",
    "COMPANY": "Company@12345",
}


@dataclass(frozen=True)
class FacultySeed:
    key: str
    email: str
    full_name: str
    department: str
    designation: str
    employee_id: str


FACULTY = [
    FacultySeed("faculty", "faculty@campushire.dev", "Dr. Ananya Rao", "CSE", "Associate Professor", "EMP-1001"),
    FacultySeed("faculty2", "faculty2@campushire.dev", "Prof. Vikram Shah", "ECE", "Professor", "EMP-1002"),
]


@dataclass(frozen=True)
class StudentSeed:
    key: str
    email: str
    full_name: str
    department: str
    gpa: str
    graduation_year: int
    verified: bool = True


STUDENTS = [
    StudentSeed("student", "student@campushire.dev", "Aarav Mehta", "CSE", "3.72", 2027),
    StudentSeed("student2", "student2@campushire.dev", "Diya Nair", "CSE", "3.50", 2027),
    StudentSeed("student3", "student3@campushire.dev", "Rohan Iyer", "ECE", "3.20", 2026),
    StudentSeed("student4", "student4@campushire.dev", "Sneha Kulkarni", "IT", "3.85", 2027),
    StudentSeed("student5", "student5@campushire.dev", "Kabir Singh", "ME", "2.60", 2026),
    StudentSeed("student6", "student6@campushire.dev", "Ishita Gupta", "MBA", "3.40", 2027),
    StudentSeed("student7", "student7@campushire.dev", "Arjun Reddy", "CSE", "3.95", 2026),
    StudentSeed("student8", "student8@campushire.dev", "Meera Pillai", "ECE", "3.05", 2027),
    StudentSeed("student9", "student9@campushire.dev", "Vihaan Joshi", "IT", "2.90", 2026),
    StudentSeed("student10", "student10@campushire.dev", "Tanvi Desai", "ME", "3.30", 2027),
    StudentSeed("student11", "student11@campushire.dev", "Rahul Verma", "MBA", "2.75", 2026),
    StudentSeed("student12", "student12@campushire.dev", "Priya Menon", "CSE", "3.60", 2027),
    StudentSeed("pending", "pending@campushire.dev", "Pending Student", "CSE", "3.10", 2028, verified=False),
]

COMPANY_USER_EMAIL = "company@campushire.dev"
COMPANY_USER_NAME = "Neha Kapoor"
COMPANY_USER_JOB_TITLE = "Talent Acquisition Lead"


@dataclass(frozen=True)
class CompanySeed:
    key: str
    name: str
    location: str
    registration_number: str
    industry: str
    website: str
    contact_person_name: str
    contact_email: str
    description: str
    status: str = "ACTIVE"


COMPANIES = [
    CompanySeed("nimbus", "Nimbus Labs", "Bengaluru, India", "U72200KA2015PTC082345", "Cloud Software",
                "https://nimbuslabs.dev", "Neha Kapoor", "careers@nimbuslabs.dev",
                "Nimbus Labs builds cloud-native developer tooling used by thousands of engineering teams."),
    CompanySeed("quantix", "Quantix Analytics", "Pune, India", "U74999MH2017PTC291234", "Data & Analytics",
                "https://quantix.dev", "Sameer Joshi", "talent@quantix.dev",
                "Quantix Analytics turns messy enterprise data into decisions with ML-driven analytics."),
    CompanySeed("orbit", "Orbit Robotics", "Hyderabad, India", "U29309TG2018PTC123456", "Robotics",
                "https://orbitrobotics.dev", "Lakshmi Rao", "hr@orbitrobotics.dev",
                "Orbit Robotics designs warehouse automation robots and embedded control firmware."),
    CompanySeed("greengrid", "GreenGrid Energy", "Chennai, India", "L40100TN2012PLC087654", "Renewable Energy",
                "https://greengrid.dev", "Arvind Kumar", "people@greengrid.dev",
                "GreenGrid Energy develops smart-grid software and solar forecasting systems."),
    CompanySeed("pixelcraft", "Pixelcraft Studios", "Remote", "US-DE5567123", "Design & Media",
                "https://pixelcraft.dev", "Hannah Brooks", "hello@pixelcraft.dev",
                "Pixelcraft Studios is a remote-first product design studio shipping apps for global brands."),
    CompanySeed("finverse", "Finverse", "Mumbai, India", "U67190MH2019PTC334455", "FinTech",
                "https://finverse.dev", "Rajesh Malhotra", "campus@finverse.dev",
                "Finverse builds payments and risk infrastructure for digital-first banks."),
    CompanySeed("skyline", "Skyline Ventures", "New Delhi, India", "U65999DL2021PTC377777", "Venture Capital",
                "https://skylineventures.dev", "Pooja Arora", "contact@skylineventures.dev",
                "Skyline Ventures is an early-stage venture fund awaiting onboarding approval.", status="PENDING"),
]


@dataclass(frozen=True)
class InternshipSeed:
    key: str
    title: str
    company: str
    owner: str  # faculty | faculty2 | company
    domain: str
    location: str
    work_mode: str
    stipend: int
    weeks: int
    status: str
    deadline_days: int = 0  # days from today
    start_gap_days: int = 10  # start = deadline + gap
    skills: tuple[str, ...] = ()
    min_gpa: str | None = None
    departments: tuple[str, ...] = ()
    openings: int = 2
    rejection_reason: str | None = None
    description: str = ""


INTERNSHIPS = [
    InternshipSeed("I1", "Frontend Engineering Intern", "nimbus", "faculty", "Software Engineering", "Bengaluru", "HYBRID",
                   25000, 12, "APPROVED", 14, 9, ("React", "TypeScript", "CSS"), "3.00", ("CSE", "IT", "ECE"), 3,
                   description="Build accessible, fast user interfaces for our developer console using React and TypeScript, "
                               "pair with senior engineers and ship features to production."),
    InternshipSeed("I2", "Cloud & DevOps Intern", "nimbus", "company", "Cloud & DevOps", "Bengaluru", "ONSITE",
                   30000, 16, "APPROVED", 18, 12, ("Docker", "Kubernetes", "CI/CD"), "3.00", (), 2,
                   description="Automate build and deployment pipelines, harden Kubernetes clusters and improve observability "
                               "for Nimbus Labs' managed platform."),
    InternshipSeed("I3", "Machine Learning Intern", "quantix", "faculty", "AI/ML", "Pune", "HYBRID",
                   40000, 16, "APPROVED", 21, 14, ("Python", "PyTorch", "Statistics"), "3.30", ("CSE", "IT", "ECE"), 2,
                   description="Prototype and evaluate machine-learning models for demand forecasting and anomaly detection "
                               "on real enterprise datasets."),
    InternshipSeed("I4", "Data Science Intern", "quantix", "faculty2", "Data Science", "Pune", "REMOTE",
                   35000, 12, "APPROVED", 25, 10, ("SQL", "Python", "Visualization"), "3.00", (), 3,
                   description="Explore datasets, build dashboards and communicate insights to client stakeholders "
                               "as part of the Quantix analytics team."),
    InternshipSeed("I5", "Robotics Firmware Intern", "orbit", "faculty2", "Hardware/Embedded", "Hyderabad", "ONSITE",
                   28000, 20, "APPROVED", 28, 15, ("C/C++", "RTOS", "Embedded"), "2.80", ("ECE", "ME"), 2,
                   description="Write and test real-time firmware for warehouse robots, working with the controls and "
                               "hardware teams on sensors and motor drivers."),
    InternshipSeed("I6", "Energy Analytics Research Intern", "greengrid", "faculty", "Research", "Chennai", "HYBRID",
                   22000, 24, "APPROVED", 30, 18, ("Python", "Time Series", "Research"), "3.20", (), 1,
                   description="Research solar generation forecasting methods, run experiments and co-author an internal "
                               "technical report with GreenGrid scientists."),
    InternshipSeed("I7", "Product Design Intern", "pixelcraft", "faculty2", "Product Design", "Remote", "REMOTE",
                   15000, 10, "APPROVED", 33, 8, ("Figma", "Prototyping", "UX Research"), None, (), 2,
                   description="Design end-to-end mobile app flows, run usability tests and hand off polished Figma "
                               "specifications to engineering."),
    InternshipSeed("I8", "Product Management Intern", "pixelcraft", "faculty", "Product Management", "Remote", "REMOTE",
                   18000, 12, "APPROVED", 35, 7, ("Roadmapping", "Analytics", "Communication"), None, ("MBA", "CSE", "IT"), 1,
                   description="Support product managers with market research, backlog grooming and success metrics "
                               "for a portfolio of consumer apps."),
    InternshipSeed("I9", "Quantitative Finance Intern", "finverse", "faculty2", "Finance", "Mumbai", "ONSITE",
                   45000, 12, "APPROVED", 37, 11, ("Statistics", "Python", "Risk"), "3.50", ("MBA", "CSE", "IT"), 2,
                   description="Build risk models and back-test credit-scoring strategies alongside Finverse's quantitative "
                               "analysts."),
    InternshipSeed("I10", "Marketing Analytics Intern", "greengrid", "faculty", "Marketing", "Chennai", "HYBRID",
                   0, 8, "APPROVED", 39, 13, ("Excel", "Storytelling", "SEO"), None, ("MBA",), 2,
                   description="Analyse campaign performance, craft content for sustainability campaigns and report on "
                               "funnel metrics to the marketing head."),
    InternshipSeed("I11", "Security Operations Intern", "nimbus", "company", "Cybersecurity", "Bengaluru", "ONSITE",
                   30000, 14, "APPROVED", 40, 20, ("Networking", "Linux", "Security"), "3.00", ("CSE", "IT", "ECE"), 2,
                   description="Monitor security alerts, assist with incident response drills and help harden "
                               "Nimbus Labs' production infrastructure."),
    InternshipSeed("P1", "Supply Chain Operations Intern", "orbit", "faculty2", "Operations", "Hyderabad", "ONSITE",
                   20000, 10, "PENDING_APPROVAL", 22, 10, ("Excel", "Logistics"), None, ("ME", "MBA"), 2,
                   description="Optimise inbound logistics and spare-parts planning for Orbit Robotics' manufacturing "
                               "operations."),
    InternshipSeed("P2", "Platform Engineering Intern", "nimbus", "company", "Software Engineering", "Bengaluru", "HYBRID",
                   32000, 16, "PENDING_APPROVAL", 30, 12, ("Go", "Distributed Systems"), "3.20", ("CSE", "IT"), 2,
                   description="Work on the internal developer platform: service templates, APIs and tooling used by "
                               "all Nimbus Labs engineering teams."),
    InternshipSeed("D1", "Data Engineering Intern", "quantix", "faculty", "Data Science", "Pune", "HYBRID",
                   30000, 12, "DRAFT", 45, 10, ("SQL", "Spark", "Airflow"), "3.00", (), 2,
                   description="Draft posting: build reliable batch and streaming data pipelines for Quantix analytics products."),
    InternshipSeed("C1", "Backend Engineering Intern (Summer)", "nimbus", "faculty", "Software Engineering", "Bengaluru", "ONSITE",
                   26000, 13, "CLOSED", 0, 0, ("Java", "PostgreSQL", "REST"), "3.00", ("CSE", "IT", "ECE"), 4,
                   description="Summer programme (completed): built REST services and database tooling with the Nimbus Labs "
                               "backend team."),
    InternshipSeed("R1", "Social Media Intern", "greengrid", "faculty2", "Marketing", "Chennai", "REMOTE",
                   0, 20, "REJECTED", 25, 10, ("Writing", "Social Media"), None, ("MBA",), 1,
                   rejection_reason="Stipend is too low for a 20-week full-time programme. Please add a stipend or shorten the duration.",
                   description="Run social channels for GreenGrid Energy and create short-form content for sustainability "
                               "campaigns."),
]

SKILL_POOL = [
    "Python", "Java", "C++", "JavaScript", "TypeScript", "React", "SQL", "Docker", "Git", "Machine Learning",
    "Data Analysis", "Embedded C", "CAD", "Excel", "Communication", "Figma", "Linux", "REST APIs",
]


@dataclass
class ApplicationSeed:
    student: str
    internship: str
    status: str
    flags: dict[str, object] = field(default_factory=dict)


def app(student: str, internship: str, status: str, **flags: object) -> ApplicationSeed:
    return ApplicationSeed(student, internship, status, flags)


APPLICATIONS = [
    # student@ (5): PENDING, UNDER_REVIEW, SHORTLISTED, INTERVIEW (+3 days), ACCEPTED on the CLOSED internship
    app("student", "I2", "PENDING"),
    app("student", "I3", "UNDER_REVIEW"),
    app("student", "I4", "SHORTLISTED"),
    app("student", "I6", "INTERVIEW", interview_in_days=3),
    app("student", "C1", "ACCEPTED", completed=True),
    app("student2", "I3", "SHORTLISTED", cancelled_interview_in_days=5),
    app("student2", "I4", "PENDING"),
    app("student2", "I11", "UNDER_REVIEW"),
    app("student3", "I5", "INTERVIEW", interview_in_days=2),
    app("student3", "I1", "PENDING"),
    app("student3", "C1", "ACCEPTED", completed=True, past_interview="PASS"),
    app("student4", "I1", "SHORTLISTED"),
    app("student4", "I2", "INTERVIEW", interview_in_days=4),
    app("student4", "I11", "ACCEPTED"),
    app("student4", "C1", "ACCEPTED", completed=True, past_interview="PASS"),
    app("student5", "I5", "PENDING", stale_resume=True),
    app("student5", "I7", "REJECTED"),
    app("student6", "I10", "UNDER_REVIEW"),
    app("student6", "I9", "PENDING"),
    app("student6", "I8", "REJECTED"),
    app("student7", "I3", "INTERVIEW", interview_in_days=6),
    app("student7", "I1", "ACCEPTED"),
    app("student7", "I4", "SHORTLISTED"),
    app("student7", "C1", "ACCEPTED", completed=True, past_interview="PASS"),
    app("student8", "I5", "SHORTLISTED"),
    app("student8", "I7", "WITHDRAWN"),
    app("student8", "I1", "REJECTED", past_interview="FAIL"),
    app("student9", "I2", "PENDING"),
    app("student9", "I6", "UNDER_REVIEW"),
    app("student10", "I5", "ACCEPTED"),
    app("student10", "I6", "REJECTED"),
    app("student10", "I10", "WITHDRAWN"),
    app("student11", "I9", "REJECTED"),
    app("student11", "I10", "PENDING"),
    app("student12", "I2", "UNDER_REVIEW"),
    app("student12", "I3", "PENDING"),
    app("student12", "I4", "REJECTED"),
    app("student12", "I8", "SHORTLISTED"),
]

# (student, internship, evaluator, shared_with_student, recommendation, scores per criterion)
EVALUATIONS = [
    ("student", "I4", "faculty2", True, "YES", [4, 4, 5, 4, 4]),
    ("student7", "I4", "faculty2", False, "STRONG_YES", [5, 5, 4, 5, 5]),
    ("student4", "I1", "faculty", False, "YES", [4, 5, 4, 3, 4]),
    ("student", "C1", "faculty", True, "STRONG_YES", [5, 4, 5, 4, 5]),
    ("student7", "C1", "faculty", False, "STRONG_YES", [5, 5, 5, 4, 5]),
    ("student4", "I2", "company", False, "MAYBE", [3, 3, 4, 4, 3]),
]

# student feedback on the CLOSED internship: (student, days_ago, culture, mentorship, learning, environment, overall, comment)
STUDENT_FEEDBACK = [
    ("student3", 150, 4, 3, 4, 4, 4, "Great exposure to production systems, mentoring could be more structured."),
    ("student4", 110, 5, 5, 5, 4, 5, "Outstanding team and mentors. I learned more in 13 weeks than in a year of classes."),
    ("student7", 70, 4, 4, 5, 5, 5, "Challenging projects and very supportive reviewers."),
    ("student", 20, 5, 4, 4, 5, 4, "Friendly culture and meaningful work. Onboarding documentation could be improved."),
]

SYSTEM_FEEDBACK = [
    ("student", "FEATURE", "Calendar sync for interviews", "Please add an ICS or Google Calendar sync for upcoming interviews.", None, "NEW", None),
    ("student2", "BUG", "Resume upload stalls at 95%", "On a slow connection the resume progress bar freezes at 95% until I refresh the page.", "MEDIUM", "TRIAGED", "HIGH"),
    ("faculty", "IMPROVEMENT", "Bulk shortlist from review screen", "Selecting many candidates and shortlisting them at once would save a lot of time.", None, "PLANNED", "MEDIUM"),
    ("company", "BUG", "Duplicate notification emails", "I receive two emails whenever a candidate withdraws their application.", "LOW", "IN_PROGRESS", "LOW"),
    ("faculty2", "FEATURE", "Export evaluations to Excel", "Allow exporting all evaluations of an internship to an Excel sheet.", None, "DONE", "MEDIUM"),
    ("student3", "IMPROVEMENT", "Dark mode contrast", "Some badges are hard to read in dark mode.", None, "WONT_DO", None),
]
