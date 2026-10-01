"""ReportLab sample resume generator (the PDF engine of the project is ReportLab only)."""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer


def build_resume_pdf(
    name: str,
    email: str,
    phone: str,
    department: str,
    gpa: str,
    graduation_year: int,
    skills: list[str],
    summary: str,
) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"{name} - Resume",
        author=name,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("Title", parent=styles["Title"], fontSize=22, textColor=colors.HexColor("#4F46E5"), alignment=0)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, textColor=colors.HexColor("#111827"), spaceBefore=10)
    body = styles["BodyText"]

    story = [
        Paragraph(name, title),
        Paragraph(f"{email} &nbsp;|&nbsp; {phone}", body),
        HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#4F46E5"), spaceBefore=4, spaceAfter=6),
        Paragraph("Summary", h2),
        Paragraph(summary, body),
        Paragraph("Education", h2),
        Paragraph(f"B.Tech / MBA candidate, <b>{department}</b> - Expected graduation {graduation_year} - GPA {gpa} / 4.0", body),
        Paragraph("Skills", h2),
        Paragraph(", ".join(skills), body),
        Paragraph("Projects", h2),
        Paragraph(f"<b>Campus Placement Tracker</b> - Built a full-stack tracker using {skills[0]} and {skills[-1]}.", body),
        Spacer(1, 3 * mm),
        Paragraph(f"<b>Department Hackathon Winner</b> - Led a team of four to deliver a working prototype in 24 hours.", body),
    ]
    doc.build(story)
    return buf.getvalue()
