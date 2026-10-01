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
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useCreateInternship } from "@/lib/api/hooks/internships";
import { useCompanies } from "@/lib/api/hooks/companies";
import { INTERNSHIP_DOMAINS, DEPARTMENTS, computeDurationWeeks } from "@/lib/validation/internship";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import type { WorkMode } from "@/lib/api/types";
import { ArrowLeft, Plus, X, Building2, Calendar, Sparkles } from "lucide-react";

export default function NewInternshipPage() {
  const router = useRouter();
  const createInternship = useCreateInternship();
  const { data: companiesData } = useCompanies({ page_size: 100 });

  const [companyId, setCompanyId] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [requirements, setRequirements] = useState("");
  const [domain, setDomain] = useState<string>(INTERNSHIP_DOMAINS[0]);
  const [department, setDepartment] = useState<string>(DEPARTMENTS[0]);
  const [location, setLocation] = useState("");
  const [workMode, setWorkMode] = useState<WorkMode>("HYBRID");
  const [stipend, setStipend] = useState<number | string>(15000);
  const [minGpa, setMinGpa] = useState<number | string>(3.0);
  const [openings, setOpenings] = useState<number | string>(2);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [deadline, setDeadline] = useState("");
  const [skills, setSkills] = useState<string[]>(["Python", "Git"]);
  const [newSkill, setNewSkill] = useState("");

  const duration = computeDurationWeeks(startDate, endDate) || 8;

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
    if (!companyId) {
      toast.error("Please select a partner company.");
      return;
    }
    if (!startDate || !endDate || !deadline) {
      toast.error("Please fill in start date, end date, and application deadline.");
      return;
    }

    createInternship.mutate(
      {
        company_id: companyId,
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
        onSuccess: (res) => {
          toast.success("Internship posting created in DRAFT status");
          router.push(`/faculty/internships`);
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
          href="/faculty/internships"
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-3 transition-colors"
        >
          <ArrowLeft className="size-3.5" /> Back to postings
        </Link>
        <PageHeader
          title="Create Internship Posting"
          description="Publish a new recruitment opportunity with eligibility criteria and target skills."
        />
      </div>

      <form onSubmit={handleSubmit}>
        <Card className="rounded-2xl border-border/60 shadow-sm space-y-6 p-6">
          <div className="grid gap-6 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="company">Corporate Partner / Employer</Label>
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
            </div>

            <div className="space-y-2">
              <Label htmlFor="title">Position Title</Label>
              <Input
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Full Stack Engineering Intern"
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
              <Label htmlFor="dept">Target Department</Label>
              <Select value={department} onValueChange={setDepartment}>
                <SelectTrigger id="dept" className="rounded-xl">
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
              <Label htmlFor="workMode">Work Arrangement</Label>
              <Select value={workMode} onValueChange={(v) => setWorkMode(v as WorkMode)}>
                <SelectTrigger id="workMode" className="rounded-xl">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="rounded-xl">
                  <SelectItem value="REMOTE">Remote</SelectItem>
                  <SelectItem value="HYBRID">Hybrid</SelectItem>
                  <SelectItem value="ONSITE">On-Site</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid gap-6 sm:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="location">Work Location / City</Label>
              <Input
                id="location"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g. Bangalore, India"
                required
                className="rounded-xl"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="stipend">Monthly Stipend (₹)</Label>
              <Input
                id="stipend"
                type="number"
                min="0"
                value={stipend}
                onChange={(e) => setStipend(e.target.value)}
                placeholder="15000"
                className="rounded-xl"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="minGpa">Minimum Required GPA</Label>
              <Input
                id="minGpa"
                type="number"
                step="0.1"
                min="0"
                max="4"
                value={minGpa}
                onChange={(e) => setMinGpa(e.target.value)}
                placeholder="3.0"
                className="rounded-xl"
              />
            </div>
          </div>

          <div className="grid gap-6 sm:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="startDate">Start Date</Label>
              <Input
                id="startDate"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
                className="rounded-xl"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="endDate">End Date</Label>
              <Input
                id="endDate"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                required
                className="rounded-xl"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="deadline">Application Deadline</Label>
              <Input
                id="deadline"
                type="date"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                required
                className="rounded-xl"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Job Description & Responsibilities</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Outline the responsibilities, project goals, and daily tasks..."
              rows={4}
              required
              className="rounded-xl"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="reqs">Candidate Qualifications & Eligibility</Label>
            <Textarea
              id="reqs"
              value={requirements}
              onChange={(e) => setRequirements(e.target.value)}
              placeholder="Academic requirements, prior coursework, prerequisites..."
              rows={3}
              className="rounded-xl"
            />
          </div>

          <div className="space-y-2">
            <Label>Required Technologies & Skills</Label>
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
                placeholder="Add a required skill..."
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

          <div className="flex items-center justify-between border-t pt-4">
            <Button variant="outline" asChild className="rounded-xl">
              <Link href="/faculty/internships">Cancel</Link>
            </Button>
            <Button type="submit" disabled={createInternship.isPending} className="rounded-xl">
              {createInternship.isPending ? "Creating..." : "Save Draft Posting"}
            </Button>
          </div>
        </Card>
      </form>
    </div>
  );
}
