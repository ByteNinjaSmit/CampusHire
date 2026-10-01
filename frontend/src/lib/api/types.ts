// API CONTRACT: PLAN.md section 6, copied verbatim. Do not edit without updating the plan and the backend schemas.
// Extra shapes that the plan does not define live in ./types-extra.ts.

// ---------- 6.1 Common ----------
export type UUID = string; export type ISODateTime = string; export type ISODate = string;
export type Role = "ADMIN" | "FACULTY" | "STUDENT" | "COMPANY";
export interface Page<T> { items: T[]; total: number; page: number; page_size: number; pages: number; }
export interface ApiErrorBody { error: { code: string; message: string; details?: { field: string; message: string }[]; request_id?: string } }
export interface MessageResponse { message: string }
export type ApplicationStatus = "PENDING"|"UNDER_REVIEW"|"SHORTLISTED"|"INTERVIEW"|"ACCEPTED"|"REJECTED"|"WITHDRAWN";
export type InternshipStatus = "DRAFT"|"PENDING_APPROVAL"|"APPROVED"|"REJECTED"|"CLOSED";
export type CompanyStatus = "PENDING"|"ACTIVE"|"ARCHIVED";
export type WorkMode = "ONSITE"|"REMOTE"|"HYBRID";
export type InterviewStatus = "SCHEDULED"|"RESCHEDULED"|"COMPLETED"|"CANCELLED"|"NO_SHOW";
export type InterviewResult = "PENDING"|"PASS"|"FAIL"|"ON_HOLD";
export type InterviewMode = "ONLINE"|"ONSITE"|"PHONE";
export type DocumentKind = "RESUME"|"COVER_LETTER"|"TRANSCRIPT"|"OFFER_LETTER"|"LOGO"|"REPORT"|"EXPORT"|"IMPORT"|"OTHER";
export type JobStatus = "QUEUED"|"RUNNING"|"SUCCEEDED"|"FAILED";

// ---------- 6.2 Auth and users ----------
export interface StudentRegisterRequest { email: string; password: string; full_name: string; phone: string; department: string; gpa: number; enrollment_no?: string; graduation_year?: number }
export interface CompanyRegisterRequest { email: string; password: string; full_name: string; phone?: string; job_title?: string;
  company: { name: string; registration_number: string; location: string; industry?: string; website?: string; contact_person_name: string; contact_email: string; contact_phone?: string } }
export interface LoginRequest { email: string; password: string }
export interface Me { id: UUID; email: string; role: Role; full_name: string; phone: string|null; avatar_url: string|null; email_verified: boolean; is_active: boolean; created_at: ISODateTime;
  student?: StudentProfile; faculty?: FacultyProfile; company?: { company_id: UUID; company_name: string; company_status: CompanyStatus; job_title: string|null } }
export interface TokenResponse { access_token: string; token_type: "bearer"; expires_in: number; user: Me }
export interface UserSummary { id: UUID; email: string; role: Role; full_name: string; phone: string|null; is_active: boolean; email_verified: boolean; last_login_at: ISODateTime|null; created_at: ISODateTime }
export interface AdminCreateUserRequest { email: string; password: string; full_name: string; role: Role; phone?: string; mark_verified?: boolean;
  student?: { department: string; gpa: number; enrollment_no?: string; graduation_year?: number };
  faculty?: { department: string; designation?: string; employee_id?: string };
  company?: { company_id: UUID; job_title?: string } }
export interface UpdateUserRequest { full_name?: string; phone?: string|null; student?: Partial<StudentProfileUpdate>; faculty?: Partial<FacultyProfile> }

// ---------- 6.3 Students, faculty, companies ----------
export interface StudentProfile { user_id: UUID; department: string; gpa: number; enrollment_no: string|null; graduation_year: number|null; skills: string[]; bio: string|null;
  linkedin_url: string|null; github_url: string|null; portfolio_url: string|null; default_resume: DocumentSummary|null }
export interface StudentProfileUpdate { phone?: string; department?: string; gpa?: number; graduation_year?: number|null; skills?: string[]; bio?: string|null; linkedin_url?: string|null; github_url?: string|null; portfolio_url?: string|null }
export interface StudentListItem { user_id: UUID; full_name: string; email: string; phone: string|null; department: string; gpa: number; is_active: boolean; application_count: number; placed: boolean }
export interface StudentDetail extends StudentListItem { profile: StudentProfile; stats: { total_applications: number; by_status: Record<ApplicationStatus, number>; interviews_upcoming: number } }
export interface FacultyProfile { user_id: UUID; department: string; designation: string|null; employee_id: string|null }
export interface CompanySummary { id: UUID; name: string; registration_number: string; industry: string|null; location: string; logo_url: string|null; status: CompanyStatus; avg_rating: number|null; rating_count: number; open_internships: number }
export interface Company extends CompanySummary { website: string|null; description: string|null; contact_person_name: string; contact_email: string; contact_phone: string|null; archived_at: ISODateTime|null; created_at: ISODateTime;
  rating_summary: RatingSummary }
export interface CompanyCreateRequest { name: string; registration_number: string; location: string; industry?: string; website?: string; description?: string; contact_person_name: string; contact_email: string; contact_phone?: string; logo_document_id?: UUID }
export interface RatingSummary { count: number; overall: number|null; company_culture: number|null; mentorship: number|null; technical_learning: number|null; work_environment: number|null;
  distribution: Record<"1"|"2"|"3"|"4"|"5", number> }

// ---------- 6.4 Internships ----------
export interface InternshipSummary { id: UUID; title: string; domain: string; location: string; work_mode: WorkMode; stipend_monthly: number; currency: string;
  duration_weeks: number; start_date: ISODate; end_date: ISODate; application_deadline: ISODateTime; status: InternshipStatus; skills: string[];
  company: { id: UUID; name: string; logo_url: string|null; avg_rating: number|null }; is_saved: boolean; application_count?: number; archived_at: ISODateTime|null; created_at: ISODateTime }
export interface Internship extends InternshipSummary { description: string; openings: number; min_gpa: number|null; eligible_departments: string[];
  posted_by: { id: UUID; full_name: string; role: Role }; rejection_reason: string|null; approved_at: ISODateTime|null;
  my_application: { id: UUID; status: ApplicationStatus } | null; can_edit: boolean; can_apply: boolean }
export interface InternshipCreateRequest { company_id: UUID; title: string; description: string; domain: string; location: string; work_mode: WorkMode; stipend_monthly: number; currency?: string;
  duration_weeks?: number; start_date: ISODate; end_date: ISODate; application_deadline: ISODateTime; openings?: number; skills?: string[]; min_gpa?: number|null; eligible_departments?: string[]; submit?: boolean }
export type InternshipUpdateRequest = Partial<Omit<InternshipCreateRequest,"company_id"|"submit">>;
export interface InternshipFacets { domains: {value: string; count: number}[]; locations: {value: string; count: number}[]; companies: {id: UUID; name: string; count: number}[];
  work_modes: {value: WorkMode; count: number}[]; stipend: { min: number; max: number } }
export interface BulkActionResult { updated: UUID[]; failed: { id: UUID; code: string; message: string }[] }

// ---------- 6.5 Applications ----------
export interface ApplicationCreateRequest { internship_id: UUID; resume_document_id: UUID; cover_letter: string; qualifications: string;
  answers?: { skills?: string[]; coursework?: string; availability_from?: ISODate; portfolio_url?: string } }
export interface ApplicationSummary { id: UUID; status: ApplicationStatus; status_changed_at: ISODateTime; created_at: ISODateTime;
  internship: { id: UUID; title: string; company_id: UUID; company_name: string; company_logo_url: string|null; application_deadline: ISODateTime; start_date: ISODate };
  student: { id: UUID; full_name: string; email: string; department: string; gpa: number }; next_interview_at: ISODateTime|null; evaluation_avg: number|null }
export interface TimelineEvent { at: ISODateTime; kind: "STATUS"|"INTERVIEW_SCHEDULED"|"INTERVIEW_RESCHEDULED"|"INTERVIEW_CANCELLED"|"INTERVIEW_COMPLETED"|"EVALUATION"|"COMPLETED";
  status?: ApplicationStatus; title: string; note: string|null; actor_name: string|null }
export interface ApplicationDetail extends ApplicationSummary { cover_letter: string; qualifications: string; answers: Record<string, unknown>; resume: DocumentSummary;
  decision_note: string|null; offer_details: OfferDetails|null; withdrawn_reason: string|null; completed_at: ISODateTime|null;
  timeline: TimelineEvent[]; interviews: Interview[]; evaluations: EvaluationSummary[];
  allowed_transitions: ApplicationStatus[];   // computed for the caller
  can_give_student_feedback: boolean; student_feedback_id: UUID|null; company_feedback_ids: UUID[] }
export interface OfferDetails { stipend_monthly: number; start_date: ISODate; joining_location?: string; notes?: string }
export interface ApplicationStatusUpdateRequest { status: ApplicationStatus; note?: string; offer_details?: OfferDetails }
export interface BulkStatusRequest { ids: UUID[]; status: ApplicationStatus; note?: string }

// ---------- 6.6 Interviews ----------
export interface Interview { id: UUID; application_id: UUID; scheduled_at: ISODateTime; duration_minutes: number; mode: InterviewMode; location: string|null; meeting_link: string|null;
  interviewer_name: string; interviewer_email: string|null; status: InterviewStatus; result: InterviewResult; score: number|null;
  comments?: string|null;            // omitted for STUDENT
  feedback_for_student: string|null; cancel_reason: string|null; reschedule_count: number;
  student: { id: UUID; full_name: string }; internship: { id: UUID; title: string; company_name: string }; created_at: ISODateTime }
export interface InterviewCreateRequest { application_id: UUID; scheduled_at: ISODateTime; duration_minutes: number; mode: InterviewMode; location?: string; meeting_link?: string;
  interviewer_name: string; interviewer_email?: string; interviewer_user_id?: UUID }
export interface InterviewRescheduleRequest { scheduled_at: ISODateTime; duration_minutes?: number; reason: string }
export interface InterviewResultRequest { status: "COMPLETED"|"NO_SHOW"; result: InterviewResult; score?: number; comments?: string; feedback_for_student?: string }

// ---------- 6.7 Evaluations ----------
export interface EvaluationCriterion { id: UUID; name: string; description: string|null; weight: number; max_score: 5|10; position: number }
export interface EvaluationForm { id: UUID; name: string; description: string|null; is_default: boolean; criteria: EvaluationCriterion[]; archived_at: ISODateTime|null; created_at: ISODateTime; in_use: boolean }
export interface EvaluationFormCreateRequest { name: string; description?: string; criteria: { name: string; description?: string; weight: number; max_score: 5|10 }[] }
export interface EvaluationSummary { id: UUID; form_name: string; evaluator_name: string; weighted_score: number; recommendation: "STRONG_YES"|"YES"|"MAYBE"|"NO"; created_at: ISODateTime; shared_with_student: boolean }
export interface Evaluation extends EvaluationSummary { form_id: UUID; application_id: UUID; student: { id: UUID; full_name: string }; internship: { id: UUID; title: string };
  scores: { criterion_id: UUID; criterion_name: string; score: number; max_score: number; weight: number; comment: string|null }[]; overall_comments: string|null; archived_at: ISODateTime|null }
export interface EvaluationCreateRequest { form_id: UUID; application_id: UUID; scores: { criterion_id: UUID; score: number; comment?: string }[]; overall_comments?: string;
  recommendation: "STRONG_YES"|"YES"|"MAYBE"|"NO"; shared_with_student?: boolean }
// weighted_score = 100 * Σ(score/max_score * weight) / Σ(weight), rounded to 2 decimals

// ---------- 6.8 Feedback ----------
export interface StudentFeedbackCreateRequest { application_id: UUID; company_culture: number; mentorship: number; technical_learning: number; work_environment: number; overall: number; comments?: string; suggestions?: string; is_anonymous?: boolean }
export interface StudentFeedback extends StudentFeedbackCreateRequest { id: UUID; student_name: string|null /* null if anonymous and viewer is not ADMIN */; company: { id: UUID; name: string }; internship: { id: UUID; title: string };
  response_body: string|null; responded_by_name: string|null; responded_at: ISODateTime|null; created_at: ISODateTime }
export interface FeedbackTrends { months: string[] /* "2026-04" */; series: { dimension: "overall"|"company_culture"|"mentorship"|"technical_learning"|"work_environment"; values: (number|null)[] }[]; counts: number[] }
export interface CompanyFeedbackCreateRequest { application_id: UUID; technical_skills: number; soft_skills: number; punctuality: number; responsibility: number; teamwork: number; learning_ability: number; strengths?: string; improvements?: string; hire_likelihood: number }
export interface CompanyFeedback extends CompanyFeedbackCreateRequest { id: UUID; author_name: string; student: { id: UUID; full_name: string }; internship: { id: UUID; title: string }; average: number; created_at: ISODateTime }
export interface FacultyFeedbackCreateRequest { internship_id: UUID; application_id?: UUID; course_suitability: number; learning_outcomes: number; internship_quality: number; suggestions?: string; comments?: string }
export interface FacultyFeedback extends FacultyFeedbackCreateRequest { id: UUID; faculty_name: string; internship_title: string; created_at: ISODateTime }
export interface SystemFeedbackCreateRequest { type: "FEATURE"|"BUG"|"IMPROVEMENT"; title: string; description: string; page_url?: string; severity?: "LOW"|"MEDIUM"|"HIGH"|"CRITICAL" }
export interface SystemFeedback extends SystemFeedbackCreateRequest { id: UUID; user: { id: UUID; full_name: string; role: Role }; status: "NEW"|"TRIAGED"|"PLANNED"|"IN_PROGRESS"|"DONE"|"WONT_DO";
  priority: "LOW"|"MEDIUM"|"HIGH"|null; admin_notes: string|null; action_items: ActionItem[]; created_at: ISODateTime }
export interface ActionItem { id: UUID; title: string; assignee: { id: UUID; full_name: string }|null; status: "OPEN"|"IN_PROGRESS"|"DONE"; due_date: ISODate|null; created_at: ISODateTime }
export interface SystemFeedbackSummary { by_type: Record<string, number>; by_status: Record<string, number>; last_30_days: { date: ISODate; count: number }[]; open_action_items: number }

// ---------- 6.9 Documents, notifications, jobs ----------
export interface UploadUrlRequest { kind: DocumentKind; filename: string; content_type: string; size_bytes: number }
export interface UploadTicket { document_id: UUID; upload: { url: string; fields: Record<string, string> }; expires_in: number; max_bytes: number }
// browser: const fd = new FormData(); Object.entries(fields).forEach(([k,v])=>fd.append(k,v)); fd.append("file", file); POST upload.url → 204; then POST /documents/{id}/complete
export interface DocumentSummary { id: UUID; kind: DocumentKind; filename: string; content_type: string; size_bytes: number; status: "PENDING_UPLOAD"|"UPLOADED"|"REJECTED";
  verification_status: "PENDING"|"VERIFIED"|"REJECTED"; created_at: ISODateTime }
export interface Document extends DocumentSummary { owner: { id: UUID; full_name: string }; verification_note: string|null; verified_at: ISODateTime|null; in_use: boolean }
export interface Notification { id: UUID; type: string; title: string; body: string; link: string|null; data: Record<string, unknown>; read_at: ISODateTime|null; created_at: ISODateTime }
export interface Job { id: UUID; type: "REPORT_EXPORT"|"DATA_EXPORT"|"DATA_IMPORT"|"COMPLIANCE_SCAN"; status: JobStatus; progress: number; params: Record<string, unknown>;
  result: { rows_ok?: number; rows_failed?: number; errors?: { row: number; field: string; message: string }[] } | null; error: string|null; download_url: string|null; created_at: ISODateTime; finished_at: ISODateTime|null }

// ---------- 6.10 WebSocket (message envelope, see section 6.10) ----------
export type WsMessage =
  | { type: "notification"; data: Notification }
  | { type: "unread_count"; data: { count: number } }
  | { type: "job"; data: Job }
  | { type: "ping" };

// ---------- 6.11 Reports and analytics ----------
export interface ReportMeta { key: string; title: string; description: string; formats: ("pdf"|"xlsx")[]; params: ("from"|"to"|"internship_id"|"company_id"|"student_id")[] }
export type ReportChart =
  | { id: string; type: "line"|"bar"|"area"; title: string; x: string[]; series: { name: string; data: number[] }[] }
  | { id: string; type: "pie"|"donut"; title: string; data: { name: string; value: number }[] }
  | { id: string; type: "radar"; title: string; indicators: { name: string; max: number }[]; series: { name: string; data: number[] }[] };
export interface ReportTable { id: string; title: string; columns: { key: string; label: string; format?: "number"|"percent"|"currency"|"date"|"datetime"|"text" }[]; rows: Record<string, string|number|null>[] }
export interface Kpi { label: string; value: number|string; format?: "number"|"percent"|"currency"|"text"; delta?: number|null; hint?: string }
export interface ReportData { key: string; title: string; generated_at: ISODateTime; params: Record<string, unknown>; kpis: Kpi[]; charts: ReportChart[]; tables: ReportTable[] }
export interface DashboardData { role: Role; kpis: Kpi[]; charts: ReportChart[];
  lists: { id: string; title: string; items: { id: UUID; title: string; subtitle?: string; status?: string; at?: ISODateTime; link: string }[] }[] }
