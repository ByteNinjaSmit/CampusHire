"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useInternship } from "@/lib/api/hooks/internships";
import { useMyStudentProfile } from "@/lib/api/hooks/students";
import { useDocuments } from "@/lib/api/hooks/documents";
import { useCreateApplication } from "@/lib/api/hooks/applications";
import { useAuth } from "@/providers/AuthProvider";
import { Stepper } from "@/components/shared/Stepper";
import { FileUpload } from "@/components/shared/FileUpload";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { LoadingCardGrid } from "@/components/shared/LoadingSkeletons";
import { ErrorState } from "@/components/shared/ErrorState";
import { formatCurrency, formatDate } from "@/lib/format";
import { toast } from "sonner";
import { ApiError } from "@/lib/api/client";
import { errorMessage } from "@/lib/forms";
import type { Document } from "@/lib/api/types";
import {
  CheckCircle2,
  FileText,
  AlertTriangle,
  ArrowRight,
  ArrowLeft,
  Send,
  Building2,
  Calendar,
  Sparkles,
  Plus,
  X,
} from "lucide-react";

const STEPS = [
  { title: "Eligibility", description: "Review requirements" },
  { title: "Resume", description: "Select document" },
  { title: "Cover Letter", description: "Pitch yourself" },
  { title: "Qualifications", description: "Skills & coursework" },
  { title: "Review & Submit", description: "Final confirmation" },
];

export default function ApplyWizardPage() {
  const params = useParams();
  const id = typeof params?.id === "string" ? params.id : "";
  const { user } = useAuth();
  const router = useRouter();

  const isStudent = user?.role === "STUDENT";
  const { data: internship, isLoading: isInternshipLoading } = useInternship(id);
  const { data: studentProfile, isLoading: isStudentLoading } = useMyStudentProfile(isStudent);
  const { data: docsData, refetch: refetchDocs } = useDocuments({ kind: "RESUME", page_size: 20 }, isStudent);
  const createApplication = useCreateApplication();

  const [currentStep, setCurrentStep] = useState(0);

  // Form State
  const [resumeId, setResumeId] = useState<string>("");
  const [coverLetter, setCoverLetter] = useState<string>("");
  const [summary, setSummary] = useState<string>("");
  const [coursework, setCoursework] = useState<string>("");
  const [availabilityDate, setAvailabilityDate] = useState<string>("");
  const [portfolioUrl, setPortfolioUrl] = useState<string>("");
  const [skills, setSkills] = useState<string[]>([]);
  const [newSkill, setNewSkill] = useState("");
  const [certified, setCertified] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [createdAppId, setCreatedAppId] = useState<string | null>(null);

  const storageKey = `campushire.apply.${id}`;

  // Restore draft from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const draft = JSON.parse(saved);
        if (draft.resumeId) setResumeId(draft.resumeId);
        if (draft.coverLetter) setCoverLetter(draft.coverLetter);
        if (draft.summary) setSummary(draft.summary);
        if (draft.coursework) setCoursework(draft.coursework);
        if (draft.availabilityDate) setAvailabilityDate(draft.availabilityDate);
        if (draft.portfolioUrl) setPortfolioUrl(draft.portfolioUrl);
        if (draft.skills) setSkills(draft.skills);
      }
    } catch {
      /* ignore storage errors */
    }
  }, [storageKey]);

  // Set default resume if not chosen yet
  useEffect(() => {
    if (!resumeId && studentProfile?.default_resume_id) {
      setResumeId(studentProfile.default_resume_id);
    }
    if (skills.length === 0 && studentProfile?.skills) {
      setSkills(studentProfile.skills);
    }
    if (!portfolioUrl && studentProfile?.portfolio_url) {
      setPortfolioUrl(studentProfile.portfolio_url);
    }
  }, [studentProfile, resumeId, skills.length, portfolioUrl]);

  // Auto-save draft
  useEffect(() => {
    if (!isSuccess) {
      try {
        localStorage.setItem(
          storageKey,
          JSON.stringify({
            resumeId,
            coverLetter,
            summary,
            coursework,
            availabilityDate,
            portfolioUrl,
            skills,
          })
        );
      } catch {
        /* ignore */
      }
    }
  }, [storageKey, resumeId, coverLetter, summary, coursework, availabilityDate, portfolioUrl, skills, isSuccess]);

  if (isInternshipLoading || isStudentLoading) {
    return <LoadingCardGrid count={2} />;
  }

  if (!internship) {
    return <ErrorState title="Posting not found" description="Cannot apply to an invalid internship." />;
  }

  // Eligibility evaluation
  const deadlinePassed = new Date(internship.application_deadline) < new Date();
  const gpaEligible =
    !internship.min_gpa || (studentProfile?.gpa != null && studentProfile.gpa >= internship.min_gpa);
  const deptEligible =
    !internship.department ||
    internship.department === "ALL" ||
    (studentProfile?.department &&
      studentProfile.department.toLowerCase().includes(internship.department.toLowerCase()));

  const isEligible = !deadlinePassed && gpaEligible && deptEligible;

  const resumes = docsData?.items ?? [];
  const selectedResume = resumes.find((r) => r.id === resumeId);

  const handleAddSkill = () => {
    const trimmed = newSkill.trim();
    if (trimmed && !skills.includes(trimmed)) {
      setSkills([...skills, trimmed]);
      setNewSkill("");
    }
  };

  const handleRemoveSkill = (skillToRemove: string) => {
    setSkills(skills.filter((s) => s !== skillToRemove));
  };

  const validateCurrentStep = () => {
    if (currentStep === 0) {
      if (!isEligible) {
        toast.error("You do not meet the minimum eligibility criteria for this posting.");
        return false;
      }
      return true;
    }
    if (currentStep === 1) {
      if (!resumeId) {
        toast.error("Please select or upload a resume to proceed.");
        return false;
      }
      return true;
    }
    if (currentStep === 2) {
      if (coverLetter.trim().length < 50) {
        toast.error("Cover letter must be at least 50 characters.");
        return false;
      }
      if (coverLetter.length > 5000) {
        toast.error("Cover letter must be under 5000 characters.");
        return false;
      }
      return true;
    }
    if (currentStep === 3) {
      if (summary.trim().length < 10) {
        toast.error("Please provide a brief qualifications summary (at least 10 characters).");
        return false;
      }
      return true;
    }
    return true;
  };

  const handleNext = () => {
    if (validateCurrentStep()) {
      setCurrentStep((prev) => Math.min(STEPS.length - 1, prev + 1));
    }
  };

  const handleBack = () => {
    setCurrentStep((prev) => Math.max(0, prev - 1));
  };

  const handleSubmit = () => {
    if (!certified) {
      toast.error("Please certify that your submission is accurate.");
      return;
    }

    createApplication.mutate(
      {
        internship_id: internship.id,
        resume_id: resumeId,
        cover_letter: coverLetter.trim(),
        answers: {
          summary: summary.trim(),
          skills,
          relevant_coursework: coursework.trim(),
          availability_date: availabilityDate || null,
          portfolio_url: portfolioUrl || null,
        },
      },
      {
        onSuccess: (res) => {
          setIsSuccess(true);
          setCreatedAppId(res.id);
          try {
            localStorage.removeItem(storageKey);
          } catch {
            /* ignore */
          }
          toast.success("Application submitted successfully!");
        },
        onError: (err) => {
          if (err instanceof ApiError && err.code === "DUPLICATE_APPLICATION") {
            toast.info("You have already applied for this role. Redirecting...");
            router.push("/student/applications");
          } else {
            toast.error(errorMessage(err, "Failed to submit application"));
          }
        },
      }
    );
  };

  if (isSuccess) {
    return (
      <div className="mx-auto max-w-xl py-12 text-center space-y-6">
        <div className="mx-auto flex size-16 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-600 ring-8 ring-emerald-500/10">
          <CheckCircle2 className="size-10" />
        </div>
        <div className="space-y-2">
          <h2 className="text-2xl font-bold tracking-tight">Application Submitted!</h2>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Your application for <span className="font-semibold text-foreground">{internship.title}</span> at{" "}
            <span className="font-semibold text-foreground">{internship.company?.name}</span> has been received.
            You will be notified once faculty and hiring managers begin review.
          </p>
        </div>
        <div className="flex justify-center gap-3 pt-4">
          <Button variant="outline" asChild className="rounded-xl">
            <Link href="/internships">Explore More Internships</Link>
          </Button>
          {createdAppId && (
            <Button asChild className="rounded-xl gap-1.5">
              <Link href={`/student/applications/${createdAppId}`}>
                View Application <ArrowRight className="size-4" />
              </Link>
            </Button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <Link
          href={`/internships/${internship.id}`}
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-3 transition-colors"
        >
          <ArrowLeft className="size-3.5" /> Back to internship details
        </Link>
        <h1 className="text-2xl font-bold tracking-tight">Apply to {internship.title}</h1>
        <p className="text-sm text-muted-foreground">{internship.company?.name || "Campus Placement"}</p>
      </div>

      {/* Stepper Header */}
      <div className="rounded-2xl border border-border/60 bg-card p-4 shadow-sm">
        <Stepper steps={STEPS} current={currentStep} onStepClick={(s) => s < currentStep && setCurrentStep(s)} />
      </div>

      {/* Step 1: Overview & Eligibility */}
      {currentStep === 0 && (
        <Card className="rounded-2xl border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg">Step 1: Role Overview & Eligibility</CardTitle>
            <CardDescription>Verify that you meet all criteria specified for this opening.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="rounded-xl border p-3 bg-muted/20">
                <span className="text-xs text-muted-foreground">Stipend</span>
                <p className="font-semibold text-sm">
                  {internship.stipend_monthly ? `${formatCurrency(internship.stipend_monthly)} / mo` : "Unpaid"}
                </p>
              </div>
              <div className="rounded-xl border p-3 bg-muted/20">
                <span className="text-xs text-muted-foreground">Duration</span>
                <p className="font-semibold text-sm">{internship.duration_weeks} Weeks</p>
              </div>
              <div className="rounded-xl border p-3 bg-muted/20">
                <span className="text-xs text-muted-foreground">Mode</span>
                <p className="font-semibold text-sm">{internship.work_mode}</p>
              </div>
            </div>

            <div className="space-y-3 rounded-2xl border border-border/60 bg-muted/30 p-4">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Automated Verification
              </h4>

              <div className="flex items-center justify-between text-sm">
                <span>Minimum GPA Requirement ({internship.min_gpa ?? "None"})</span>
                {gpaEligible ? (
                  <Badge variant="outline" className="text-emerald-600 gap-1 border-emerald-500/20">
                    <CheckCircle2 className="size-3.5" /> Met ({studentProfile?.gpa ?? "N/A"})
                  </Badge>
                ) : (
                  <Badge variant="destructive" className="gap-1">
                    <AlertTriangle className="size-3.5" /> Below ({studentProfile?.gpa ?? "N/A"})
                  </Badge>
                )}
              </div>

              <div className="flex items-center justify-between text-sm">
                <span>Eligible Department ({internship.department || "All"})</span>
                {deptEligible ? (
                  <Badge variant="outline" className="text-emerald-600 gap-1 border-emerald-500/20">
                    <CheckCircle2 className="size-3.5" /> Eligible ({studentProfile?.department || "Any"})
                  </Badge>
                ) : (
                  <Badge variant="destructive" className="gap-1">
                    <AlertTriangle className="size-3.5" /> Ineligible ({studentProfile?.department || "None"})
                  </Badge>
                )}
              </div>

              <div className="flex items-center justify-between text-sm">
                <span>Application Deadline ({formatDate(internship.application_deadline)})</span>
                {deadlinePassed ? (
                  <Badge variant="destructive">Passed</Badge>
                ) : (
                  <Badge variant="outline" className="text-emerald-600 border-emerald-500/20">Active</Badge>
                )}
              </div>
            </div>

            {!isEligible && (
              <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-xs text-destructive">
                You do not meet the minimum eligibility requirements to submit an application for this posting.
              </div>
            )}
          </CardContent>
          <CardFooter className="flex justify-end border-t pt-4">
            <Button onClick={handleNext} disabled={!isEligible} className="gap-1.5 rounded-xl">
              Continue to Resume <ArrowRight className="size-4" />
            </Button>
          </CardFooter>
        </Card>
      )}

      {/* Step 2: Resume */}
      {currentStep === 1 && (
        <Card className="rounded-2xl border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg">Step 2: Choose Application Resume</CardTitle>
            <CardDescription>Select an existing uploaded resume or upload a new PDF.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {resumes.length > 0 && (
              <div className="space-y-3">
                <Label>Select from your documents</Label>
                <div className="grid gap-2">
                  {resumes.map((doc) => {
                    const isSelected = resumeId === doc.id;
                    return (
                      <div
                        key={doc.id}
                        onClick={() => setResumeId(doc.id)}
                        className={`flex cursor-pointer items-center justify-between rounded-xl border p-3.5 transition-colors ${
                          isSelected
                            ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                            : "hover:bg-muted/40"
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <FileText className={`size-5 ${isSelected ? "text-primary" : "text-muted-foreground"}`} />
                          <div>
                            <p className="font-medium text-sm">{doc.file_name}</p>
                            <p className="text-xs text-muted-foreground">
                              Status: {doc.verification_status} • Uploaded {formatDate(doc.created_at)}
                            </p>
                          </div>
                        </div>
                        {isSelected && <CheckCircle2 className="size-5 text-primary" />}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            <div className="space-y-3">
              <Label>{resumes.length > 0 ? "Or upload a fresh resume" : "Upload your resume (PDF, max 5 MB)"}</Label>
              <FileUpload
                kind="RESUME"
                label="Upload new resume"
                hint="Drag & drop your PDF resume here"
                onUploaded={(doc: Document) => {
                  toast.success("Resume uploaded");
                  refetchDocs();
                  setResumeId(doc.id);
                }}
              />
            </div>
          </CardContent>
          <CardFooter className="flex justify-between border-t pt-4">
            <Button variant="outline" onClick={handleBack} className="rounded-xl">
              Back
            </Button>
            <Button onClick={handleNext} disabled={!resumeId} className="gap-1.5 rounded-xl">
              Continue to Cover Letter <ArrowRight className="size-4" />
            </Button>
          </CardFooter>
        </Card>
      )}

      {/* Step 3: Cover Letter */}
      {currentStep === 2 && (
        <Card className="rounded-2xl border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg">Step 3: Cover Letter</CardTitle>
            <CardDescription>
              Explain why you are interested in this position and why you are a great fit (50 – 5000 characters).
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="coverLetter">Statement of Purpose / Cover Letter</Label>
                <span
                  className={`text-xs ${
                    coverLetter.length < 50 || coverLetter.length > 5000
                      ? "text-amber-500 font-medium"
                      : "text-muted-foreground"
                  }`}
                >
                  {coverLetter.length} / 5000 characters (min 50)
                </span>
              </div>
              <Textarea
                id="coverLetter"
                value={coverLetter}
                onChange={(e) => setCoverLetter(e.target.value)}
                placeholder="Dear Hiring Team, I am writing to express my strong enthusiasm for this internship..."
                rows={10}
                className="rounded-xl font-sans leading-relaxed"
              />
            </div>
          </CardContent>
          <CardFooter className="flex justify-between border-t pt-4">
            <Button variant="outline" onClick={handleBack} className="rounded-xl">
              Back
            </Button>
            <Button
              onClick={handleNext}
              disabled={coverLetter.trim().length < 50 || coverLetter.length > 5000}
              className="gap-1.5 rounded-xl"
            >
              Continue to Qualifications <ArrowRight className="size-4" />
            </Button>
          </CardFooter>
        </Card>
      )}

      {/* Step 4: Qualifications & Details */}
      {currentStep === 3 && (
        <Card className="rounded-2xl border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg">Step 4: Additional Qualifications</CardTitle>
            <CardDescription>Provide technical background, availability, and portfolio links.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="summary">Qualifications Summary</Label>
              <Textarea
                id="summary"
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                placeholder="Brief summary of projects, technical experience, or key strengths..."
                rows={3}
                required
                className="rounded-xl"
              />
            </div>

            <div className="space-y-2">
              <Label>Target Skills</Label>
              <div className="flex gap-2">
                <Input
                  value={newSkill}
                  onChange={(e) => setNewSkill(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAddSkill();
                    }
                  }}
                  placeholder="Add skill..."
                  className="rounded-xl"
                />
                <Button type="button" variant="secondary" onClick={handleAddSkill} className="rounded-xl">
                  <Plus className="size-4" /> Add
                </Button>
              </div>
              <div className="flex flex-wrap gap-1.5 pt-2">
                {skills.map((s) => (
                  <Badge key={s} variant="secondary" className="gap-1 rounded-lg px-2.5 py-1 text-xs">
                    {s}
                    <button type="button" onClick={() => handleRemoveSkill(s)}>
                      <X className="size-3 text-muted-foreground hover:text-foreground" />
                    </button>
                  </Badge>
                ))}
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="coursework">Relevant Coursework</Label>
                <Input
                  id="coursework"
                  value={coursework}
                  onChange={(e) => setCoursework(e.target.value)}
                  placeholder="Data Structures, Operating Systems, Cloud Computing"
                  className="rounded-xl"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="avail">Earliest Available Date</Label>
                <Input
                  id="avail"
                  type="date"
                  value={availabilityDate}
                  onChange={(e) => setAvailabilityDate(e.target.value)}
                  className="rounded-xl"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="portfolio">Portfolio / Project Link</Label>
              <Input
                id="portfolio"
                type="url"
                value={portfolioUrl}
                onChange={(e) => setPortfolioUrl(e.target.value)}
                placeholder="https://github.com/yourhandle or portfolio website"
                className="rounded-xl"
              />
            </div>
          </CardContent>
          <CardFooter className="flex justify-between border-t pt-4">
            <Button variant="outline" onClick={handleBack} className="rounded-xl">
              Back
            </Button>
            <Button onClick={handleNext} disabled={summary.trim().length < 10} className="gap-1.5 rounded-xl">
              Review Application <ArrowRight className="size-4" />
            </Button>
          </CardFooter>
        </Card>
      )}

      {/* Step 5: Review & Submit */}
      {currentStep === 4 && (
        <Card className="rounded-2xl border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg">Step 5: Review & Submit Application</CardTitle>
            <CardDescription>Confirm your details before final submission to the recruiter.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="rounded-xl border border-border/60 divide-y text-xs">
              <div className="flex justify-between p-3">
                <span className="text-muted-foreground">Position</span>
                <span className="font-semibold text-foreground">{internship.title}</span>
              </div>
              <div className="flex justify-between p-3">
                <span className="text-muted-foreground">Company</span>
                <span className="font-semibold text-foreground">{internship.company?.name}</span>
              </div>
              <div className="flex justify-between p-3">
                <span className="text-muted-foreground">Selected Resume</span>
                <span className="font-medium text-foreground">
                  {selectedResume?.file_name || "Resume Document"}
                </span>
              </div>
              <div className="p-3 space-y-1">
                <span className="text-muted-foreground">Cover Letter Preview</span>
                <p className="line-clamp-3 text-foreground whitespace-pre-line leading-relaxed">
                  {coverLetter}
                </p>
              </div>
              <div className="p-3 space-y-1">
                <span className="text-muted-foreground">Highlighted Skills</span>
                <div className="flex flex-wrap gap-1 pt-1">
                  {skills.map((s) => (
                    <Badge key={s} variant="secondary" className="text-[10px]">
                      {s}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex items-start space-x-3 rounded-xl bg-muted/40 p-4">
              <Checkbox
                id="certify"
                checked={certified}
                onCheckedChange={(checked) => setCertified(!!checked)}
                className="mt-0.5 rounded-md"
              />
              <Label htmlFor="certify" className="text-xs leading-normal text-muted-foreground cursor-pointer">
                I hereby certify that all information submitted is true and complete to the best of my knowledge, and
                complies with the institution&apos;s code of placement ethics.
              </Label>
            </div>
          </CardContent>
          <CardFooter className="flex justify-between border-t pt-4">
            <Button variant="outline" onClick={handleBack} className="rounded-xl">
              Back
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={!certified || createApplication.isPending}
              className="gap-2 rounded-xl"
            >
              <Send className="size-4" />
              {createApplication.isPending ? "Submitting..." : "Submit Application"}
            </Button>
          </CardFooter>
        </Card>
      )}
    </div>
  );
}
