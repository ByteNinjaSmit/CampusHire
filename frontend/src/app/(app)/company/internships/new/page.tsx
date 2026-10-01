"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useCreateInternship } from "@/lib/api/hooks/internships";
import { useCompanies } from "@/lib/api/hooks/companies";
import { useAuth } from "@/providers/AuthProvider";
import { INTERNSHIP_DOMAINS, DEPARTMENTS, computeDurationWeeks } from "@/lib/validation/internship";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import type { WorkMode } from "@/lib/api/types";
import { ArrowLeft, Plus, X, Building2, Calendar, Sparkles } from "lucide-react";

export default function CompanyNewInternshipPage() {
  const router = useRouter();
  const { user } = useAuth();
  const createInternship = useCreateInternship();
  const { data: companiesData } = useCompanies({ page_size: 100 });

  const initialCompanyId = user?.company?.company_id || "";
  const [companyId, setCompanyId] = useState(initialCompanyId);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [requirements, setRequirements] = useState("");
  const [domain, setDomain] = useState<string>(INTERNSHIP_DOMAINS[0]);
  const [department, setDepartment] = useState<string>(DEPARTMENTS[0]);
  const [location, setLocation] = useState("Bengaluru, India");
  const [workMode, setWorkMode] = useState<WorkMode>("HYBRID");
  const [stipend, setStipend] = useState<number | string>(25000);
  const [minGpa, setMinGpa] = useState<number | string>(3.0);
  const [openings, setOpenings] = useState<number | string>(2);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [deadline, setDeadline] = useState("");
  const [skills, setSkills] = useState<string[]>(["Python", "Git"]);
  const [newSkill, setNewSkill] = useState("");

  const duration = computeDurationWeeks(startDate, endDate) || 12;

  const handleAddSkill = () => {
    const trimmed = newSkill.trim();
    if (trimmed && !skills.includes(trimmed)) {
      setSkills([...skills, trimmed]);
      setNewSkill("");
    }
  };

  const handleRemoveSkill = (s: string) => {
    setSkills(skills.filter((sk) => sk !== s));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const effectiveCompanyId = companyId || user?.company?.company_id;
    if (!effectiveCompanyId) {
      toast.error("Please select or confirm your company profile.");
      return;
    }
    if (!startDate || !endDate || !deadline) {
      toast.error("Please fill in start date, end date, and application deadline.");
      return;
    }

    createInternship.mutate(
      {
        company_id: effectiveCompanyId,
        title: title.trim(),
        description: description.trim(),
        requirements: requirements.trim(),
        domain,
        department,
        location: location.trim(),
        work_mode: workMode,
        stipend_monthly: Number(stipend) || 0,
        currency: "INR",
        start_date: startDate,
        end_date: endDate,
        application_deadline: deadline.includes("T") ? deadline : `${deadline}T23:59:59Z`,
        duration_weeks: duration,
        openings: Number(openings) || 1,
        min_gpa: minGpa !== "" ? Number(minGpa) : null,
        skills,
      },
      {
        onSuccess: () => {
          toast.success("Internship posting created in DRAFT status");
          router.push(`/company/internships`);
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to create internship")),
      }
    );
  };

  const companies = companiesData?.items ?? [];

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <div>
        <Link
          href="/company/internships"
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-3 transition-colors"
        >
          <ArrowLeft className="size-3.5" /> Back to postings
        </Link>
        <PageHeader
          title="Create Internship Opportunity"
          description="Publish a new recruitment opportunity with eligibility criteria and target skills."
        />
      </div>

      <form onSubmit={handleSubmit}>
        <Card className="rounded-2xl border-border/60 shadow-sm space-y-6 p-6">
          <div className="grid gap-6 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="company">Company</Label>
              {user?.company?.company_name ? (
                <div className="flex h-10 items-center rounded-xl border border-input bg-muted/40 px-3 text-sm font-medium">
                  <Building2 className="mr-2 size-4 text-primary" />
                  {user.company.company_name}
                </div>
              ) : (
                <Select value={companyId} onValueChange={setCompanyId}>
                  <SelectTrigger id="company" className="rounded-xl">
                    <SelectValue placeholder="Select Company" />
                  </SelectTrigger>
                  <SelectContent className="rounded-xl">
                    {companies.map((c) => (
                      <SelectItem key={c.id} value={c.id}>
                        {c.name} ({c.location || "Corporate"})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="title">Position Title</Label>
              <Input
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. AI Research Intern"
                required
                className="rounded-xl"
              />
            </div>
          </div>

          <div className="grid gap-6 sm:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="domain">Domain / Field</Label>
              <Select value={domain} onValueChange={setDomain}>
                <SelectTrigger id="domain" className="rounded-xl">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="rounded-xl">
                  {INTERNSHIP_DOMAINS.map((d) => (
                    <SelectItem key={d} value={d}>
                      {d}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="department">Target Department</Label>
              <Select value={department} onValueChange={setDepartment}>
                <SelectTrigger id="department" className="rounded-xl">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="rounded-xl">
                  {DEPARTMENTS.map((d) => (
                    <SelectItem key={d} value={d}>
                      {d}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="workMode">Work Mode</Label>
              <Select value={workMode} onValueChange={(v) => setWorkMode(v as WorkMode)}>
                <SelectTrigger id="workMode" className="rounded-xl">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="rounded-xl">
                  <SelectItem value="ONSITE">On-Site</SelectItem>
                  <SelectItem value="HYBRID">Hybrid</SelectItem>
                  <SelectItem value="REMOTE">Remote</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid gap-6 sm:grid-cols-4">
            <div className="space-y-2">
              <Label htmlFor="location">Location</Label>
              <Input
                id="location"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="City, Country"
                required
                className="rounded-xl"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="stipend">Stipend (Monthly ₹)</Label>
              <Input
                id="stipend"
                type="number"
                min="0"
                step="500"
                value={stipend}
                onChange={(e) => setStipend(e.target.value)}
                required
                className="rounded-xl"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="minGpa">Min GPA (out of 4.0)</Label>
              <Input
                id="minGpa"
                type="number"
                step="0.01"
                min="0"
                max="4"
                value={minGpa}
                onChange={(e) => setMinGpa(e.target.value)}
                placeholder="Optional"
                className="rounded-xl"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="openings">Openings</Label>
              <Input
                id="openings"
                type="number"
                min="1"
                value={openings}
                onChange={(e) => setOpenings(e.target.value)}
                required
                className="rounded-xl"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Job Description</Label>
            <Textarea
              id="description"
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the role responsibilities, team structure, and projects..."
              required
              className="rounded-xl"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="requirements">Requirements & Prerequisites</Label>
            <Textarea
              id="requirements"
              rows={3}
              value={requirements}
              onChange={(e) => setRequirements(e.target.value)}
              placeholder="Course prerequisites, year of study, required project experience..."
              className="rounded-xl"
            />
          </div>

          <div className="space-y-3">
            <Label>Required Skills</Label>
            <div className="flex flex-wrap gap-2">
              {skills.map((s) => (
                <Badge key={s} variant="secondary" className="gap-1 rounded-lg px-2.5 py-1 text-xs">
                  {s}
                  <button
                    type="button"
                    onClick={() => handleRemoveSkill(s)}
                    className="hover:text-destructive"
                  >
                    <X className="size-3" />
                  </button>
                </Badge>
              ))}
            </div>
            <div className="flex max-w-sm gap-2">
              <Input
                value={newSkill}
                onChange={(e) => setNewSkill(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleAddSkill();
                  }
                }}
                placeholder="Add a skill (e.g. React, SQL)"
                className="rounded-xl"
              />
              <Button type="button" variant="outline" onClick={handleAddSkill} className="rounded-xl">
                <Plus className="size-4" /> Add
              </Button>
            </div>
          </div>

          <div className="grid gap-6 rounded-xl border border-border/40 bg-muted/20 p-4 sm:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="startDate" className="flex items-center gap-1.5 text-xs font-semibold">
                <Calendar className="size-3.5 text-primary" /> Start Date
              </Label>
              <Input
                id="startDate"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
                className="rounded-xl bg-card"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="endDate" className="flex items-center gap-1.5 text-xs font-semibold">
                <Calendar className="size-3.5 text-primary" /> End Date
              </Label>
              <Input
                id="endDate"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                required
                className="rounded-xl bg-card"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="deadline" className="flex items-center gap-1.5 text-xs font-semibold">
                <Calendar className="size-3.5 text-primary" /> Application Deadline
              </Label>
              <Input
                id="deadline"
                type="date"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                required
                className="rounded-xl bg-card"
              />
            </div>

            <div className="sm:col-span-3 text-xs text-muted-foreground flex items-center justify-between">
              <span>
                Computed duration: <strong className="text-foreground">{duration} weeks</strong>
              </span>
              <span className="flex items-center gap-1 text-[11px] text-primary">
                <Sparkles className="size-3" /> Postings are created as DRAFT until submitted for admin approval
              </span>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-border/40">
            <Button variant="outline" asChild className="rounded-xl">
              <Link href="/company/internships">Cancel</Link>
            </Button>
            <Button type="submit" disabled={createInternship.isPending} className="rounded-xl gap-2">
              {createInternship.isPending ? "Creating..." : "Create Internship Posting"}
            </Button>
          </div>
        </Card>
      </form>
    </div>
  );
}
