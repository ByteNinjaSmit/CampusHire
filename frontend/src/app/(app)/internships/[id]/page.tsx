"use client";

import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useInternship, useToggleSaveInternship } from "@/lib/api/hooks/internships";
import { useMyStudentProfile } from "@/lib/api/hooks/students";
import { useApplications } from "@/lib/api/hooks/applications";
import { useAuth } from "@/providers/AuthProvider";
import { PageHeader } from "@/components/shared/PageHeader";
import { LoadingCardGrid } from "@/components/shared/LoadingSkeletons";
import { ErrorState } from "@/components/shared/ErrorState";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCurrency, formatDate, formatRelativeDate } from "@/lib/format";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import {
  Briefcase,
  Building2,
  MapPin,
  Calendar,
  Clock,
  Heart,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ArrowRight,
  ExternalLink,
  Users,
  Edit,
  GraduationCap,
} from "lucide-react";

export default function InternshipDetailPage() {
  const params = useParams();
  const id = typeof params?.id === "string" ? params.id : "";
  const { user } = useAuth();
  const router = useRouter();

  const isStudent = user?.role === "STUDENT";
  const isFaculty = user?.role === "FACULTY";
  const isAdmin = user?.role === "ADMIN";
  const isCompany = user?.role === "COMPANY";

  const { data: internship, isLoading, error, refetch } = useInternship(id);
  const { data: studentProfile } = useMyStudentProfile(isStudent);
  const { data: myAppsData } = useApplications(
    { internship_id: id, student_id: isStudent ? user?.id : undefined },
    isStudent && !!id
  );

  const toggleSave = useToggleSaveInternship();

  if (isLoading) {
    return <LoadingCardGrid count={3} />;
  }

  if (error || !internship) {
    return (
      <ErrorState
        title="Internship not found"
        description="The internship posting you are looking for does not exist or may have been removed."
        onRetry={() => refetch()}
      />
    );
  }

  const existingApp = myAppsData?.items?.[0];
  const isOwner = internship.posted_by === user?.id;

  // Eligibility evaluation
  const deadlinePassed = new Date(internship.application_deadline) < new Date();
  const gpaEligible =
    !internship.min_gpa || (studentProfile?.gpa != null && studentProfile.gpa >= internship.min_gpa);
  const deptEligible =
    !internship.department ||
    internship.department === "ALL" ||
    (studentProfile?.department &&
      studentProfile.department.toLowerCase().includes(internship.department.toLowerCase()));

  const isEligible = isStudent && !deadlinePassed && gpaEligible && deptEligible;

  const handleToggleSave = (e: React.MouseEvent) => {
    e.preventDefault();
    if (!isStudent) {
      toast.info("Only students can bookmark internships.");
      return;
    }
    toggleSave.mutate(
      { id: internship.id, saved: !!internship.is_saved },
      {
        onSuccess: () => {
          toast.success(internship.is_saved ? "Removed from saved" : "Saved to your bookmarks");
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to update bookmark")),
      }
    );
  };

  return (
    <div className="space-y-8">
      {/* Top Breadcrumb & Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Link href="/internships" className="hover:underline">
              Internships
            </Link>
            <span>/</span>
            <span>{internship.company?.name || "Posting"}</span>
          </div>

          <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
            {internship.title}
          </h1>

          <div className="flex flex-wrap items-center gap-3 pt-1 text-sm text-muted-foreground">
            <Link
              href={internship.company ? `/companies/${internship.company.id}` : "#"}
              className="inline-flex items-center gap-1.5 font-medium text-foreground hover:text-primary transition-colors"
            >
              <Building2 className="size-4 text-primary" />
              {internship.company?.name || "Campus Recruiter"}
            </Link>
            {internship.location && (
              <>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <MapPin className="size-4" /> {internship.location}
                </span>
              </>
            )}
            <span>•</span>
            <Badge variant="secondary">{internship.work_mode}</Badge>
            <span>•</span>
            <Badge variant="outline" className="text-emerald-600 dark:text-emerald-400 border-emerald-500/20">
              {internship.stipend_monthly ? `${formatCurrency(internship.stipend_monthly)} / month` : "Unpaid"}
            </Badge>
          </div>
        </div>

        {/* Action Controls for Poster / Student */}
        <div className="flex items-center gap-2 self-start">
          {isStudent && (
            <Button
              variant="outline"
              size="icon"
              onClick={handleToggleSave}
              className={`rounded-xl ${internship.is_saved ? "text-rose-500" : ""}`}
              title="Bookmark"
            >
              <Heart className={`size-4 ${internship.is_saved ? "fill-rose-500" : ""}`} />
            </Button>
          )}

          {(isOwner || isAdmin) && (
            <>
              <Button variant="outline" size="sm" asChild className="gap-1.5 rounded-xl">
                <Link href={`/faculty/internships/${internship.id}/edit`}>
                  <Edit className="size-4" /> Edit
                </Link>
              </Button>
              <Button size="sm" asChild className="gap-1.5 rounded-xl">
                <Link href={`/faculty/review/${internship.id}`}>
                  <Users className="size-4" /> Review Candidates
                </Link>
              </Button>
            </>
          )}
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Main Details (2 cols) */}
        <div className="space-y-6 lg:col-span-2">
          {/* Overview */}
          <Card className="rounded-2xl border-border/60 shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg">Role Overview</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm leading-relaxed text-foreground/90 whitespace-pre-line">
                {internship.description}
              </p>
            </CardContent>
          </Card>

          {/* Requirements & Skills */}
          <Card className="rounded-2xl border-border/60 shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg">Requirements & Key Skills</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {internship.requirements && (
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Candidate Requirements
                  </h4>
                  <p className="text-sm text-foreground/90 whitespace-pre-line leading-relaxed">
                    {internship.requirements}
                  </p>
                </div>
              )}

              {internship.skills && internship.skills.length > 0 && (
                <div className="space-y-2 pt-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Target Technologies & Competencies
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {internship.skills.map((skill) => {
                      const hasSkill = studentProfile?.skills?.includes(skill);
                      return (
                        <Badge
                          key={skill}
                          variant="secondary"
                          className={`gap-1.5 rounded-xl px-3 py-1 text-xs ${
                            isStudent && hasSkill
                              ? "bg-primary/10 text-primary border border-primary/30"
                              : ""
                          }`}
                        >
                          {isStudent && hasSkill && <CheckCircle2 className="size-3 text-primary" />}
                          {skill}
                        </Badge>
                      );
                    })}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Timeline & Duration */}
          <Card className="rounded-2xl border-border/60 shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg">Timeline & Schedule</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="rounded-xl border border-border/60 p-3 bg-muted/20">
                  <p className="text-xs text-muted-foreground">Duration</p>
                  <p className="font-semibold text-sm">{internship.duration_weeks} Weeks</p>
                </div>
                <div className="rounded-xl border border-border/60 p-3 bg-muted/20">
                  <p className="text-xs text-muted-foreground">Start Date</p>
                  <p className="font-semibold text-sm">{formatDate(internship.start_date)}</p>
                </div>
                <div className="rounded-xl border border-border/60 p-3 bg-muted/20">
                  <p className="text-xs text-muted-foreground">End Date</p>
                  <p className="font-semibold text-sm">{formatDate(internship.end_date)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar: Apply Card & Company Info (1 col) */}
        <div className="space-y-6">
          {/* Eligibility & Apply Sticky Card */}
          <Card className="rounded-2xl border-border/60 shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg">Application Details</CardTitle>
              <CardDescription>
                Deadline: <span className="font-semibold text-foreground">{formatDate(internship.application_deadline)}</span>
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {isStudent && (
                <div className="space-y-2 rounded-xl bg-muted/40 p-3.5 text-xs">
                  <p className="font-semibold text-foreground">Eligibility Check:</p>
                  <div className="flex items-center justify-between">
                    <span>Minimum GPA: {internship.min_gpa ?? "None"}</span>
                    {gpaEligible ? (
                      <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
                        <CheckCircle2 className="size-3.5" /> Met ({studentProfile?.gpa ?? "-"})
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-rose-600 dark:text-rose-400 font-medium">
                        <XCircle className="size-3.5" /> Not met ({studentProfile?.gpa ?? "-"})
                      </span>
                    )}
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Department: {internship.department || "Any"}</span>
                    {deptEligible ? (
                      <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
                        <CheckCircle2 className="size-3.5" /> Eligible
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-rose-600 dark:text-rose-400 font-medium">
                        <XCircle className="size-3.5" /> Not eligible
                      </span>
                    )}
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Deadline status</span>
                    {deadlinePassed ? (
                      <span className="text-rose-600 font-medium">Expired</span>
                    ) : (
                      <span className="text-emerald-600 font-medium">Open</span>
                    )}
                  </div>
                </div>
              )}

              {/* Status or Apply button */}
              {existingApp ? (
                <div className="space-y-2 rounded-xl border border-primary/30 bg-primary/5 p-4 text-center">
                  <CheckCircle2 className="mx-auto size-6 text-primary" />
                  <p className="text-xs font-semibold text-foreground">You applied for this role</p>
                  <Badge variant="outline" className="text-xs font-semibold">
                    Status: {existingApp.status}
                  </Badge>
                  <div className="pt-2">
                    <Button size="sm" asChild variant="default" className="w-full rounded-xl">
                      <Link href={`/student/applications/${existingApp.id}`}>View My Application</Link>
                    </Button>
                  </div>
                </div>
              ) : isStudent ? (
                <Button
                  size="lg"
                  className="w-full rounded-xl gap-2 font-semibold shadow-sm"
                  disabled={!isEligible}
                  asChild={isEligible}
                >
                  {isEligible ? (
                    <Link href={`/internships/${internship.id}/apply`}>
                      Apply Now <ArrowRight className="size-4" />
                    </Link>
                  ) : (
                    <span>
                      {deadlinePassed
                        ? "Deadline Passed"
                        : !gpaEligible
                          ? "GPA Requirement Not Met"
                          : "Department Ineligible"}
                    </span>
                  )}
                </Button>
              ) : (
                <div className="rounded-xl bg-muted/40 p-3 text-center text-xs text-muted-foreground">
                  Signed in as <span className="font-semibold capitalize">{user?.role.toLowerCase()}</span>.
                  Student login is required to apply.
                </div>
              )}
            </CardContent>
          </Card>

          {/* Company Mini Card */}
          {internship.company && (
            <Card className="rounded-2xl border-border/60 shadow-sm">
              <CardHeader className="flex flex-row items-center gap-3 pb-2">
                <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary font-bold">
                  {internship.company.name?.[0]?.toUpperCase() || <Building2 className="size-5" />}
                </div>
                <div>
                  <CardTitle className="text-base">{internship.company.name}</CardTitle>
                  <CardDescription className="text-xs">{internship.company.location}</CardDescription>
                </div>
              </CardHeader>
              <CardContent className="space-y-3 pt-2">
                {internship.company.description && (
                  <p className="text-xs text-muted-foreground line-clamp-3 leading-relaxed">
                    {internship.company.description}
                  </p>
                )}
                {internship.company.website && (
                  <a
                    href={internship.company.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                  >
                    Visit Website <ExternalLink className="size-3" />
                  </a>
                )}
                <div className="pt-1">
                  <Button variant="outline" size="sm" asChild className="w-full rounded-xl text-xs">
                    <Link href={`/companies/${internship.company.id}`}>View Company Profile</Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
