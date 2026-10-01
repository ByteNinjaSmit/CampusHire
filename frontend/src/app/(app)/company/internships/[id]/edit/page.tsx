"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingCardGrid } from "@/components/shared/LoadingSkeletons";
import { ErrorState } from "@/components/shared/ErrorState";
import { useInternship, useUpdateInternship } from "@/lib/api/hooks/internships";
import { INTERNSHIP_DOMAINS, DEPARTMENTS } from "@/lib/validation/internship";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import type { WorkMode } from "@/lib/api/types";
import { ArrowLeft, Plus, X } from "lucide-react";

export default function CompanyEditInternshipPage() {
  const params = useParams();
  const id = typeof params?.id === "string" ? params.id : "";
  const router = useRouter();

  const { data: internship, isLoading, error } = useInternship(id);
  const updateInternship = useUpdateInternship();

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [requirements, setRequirements] = useState("");
  const [domain, setDomain] = useState<string>(INTERNSHIP_DOMAINS[0]);
  const [department, setDepartment] = useState<string>(DEPARTMENTS[0]);
  const [location, setLocation] = useState("");
  const [workMode, setWorkMode] = useState<WorkMode>("HYBRID");
  const [stipend, setStipend] = useState<number | string>(0);
  const [minGpa, setMinGpa] = useState<number | string>("");
  const [openings, setOpenings] = useState<number | string>(1);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [deadline, setDeadline] = useState("");
  const [skills, setSkills] = useState<string[]>([]);
  const [newSkill, setNewSkill] = useState("");

  useEffect(() => {
    if (internship) {
      setTitle(internship.title || "");
      setDescription(internship.description || "");
      setRequirements((internship as unknown as { requirements?: string }).requirements || "");
      if (internship.domain) setDomain(internship.domain);
      if ((internship as unknown as { department?: string }).department) {
        setDepartment((internship as unknown as { department: string }).department);
      }
      setLocation(internship.location || "");
      setWorkMode(internship.work_mode || "HYBRID");
      setStipend(internship.stipend_monthly ?? 0);
      setMinGpa(internship.min_gpa ?? "");
      setOpenings(internship.openings ?? 1);
      if (internship.start_date) setStartDate(internship.start_date.substring(0, 10));
      if (internship.end_date) setEndDate(internship.end_date.substring(0, 10));
      if (internship.application_deadline) {
        setDeadline(internship.application_deadline.substring(0, 10));
      }
      if (internship.skills) setSkills(internship.skills);
    }
  }, [internship]);

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
    if (!id) return;

    updateInternship.mutate(
      {
        id,
        body: {
          title: title.trim(),
          description: description.trim(),
          domain,
          location: location.trim(),
          work_mode: workMode,
          stipend_monthly: Number(stipend) || 0,
          start_date: startDate,
          end_date: endDate,
          application_deadline: deadline.includes("T") ? deadline : `${deadline}T23:59:59Z`,
          openings: Number(openings) || 1,
          min_gpa: minGpa !== "" ? Number(minGpa) : null,
          skills,
        },
      },
      {
        onSuccess: () => {
          toast.success("Internship posting updated successfully");
          router.push(`/company/internships`);
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to update posting")),
      }
    );
  };

  if (isLoading) return <LoadingCardGrid count={2} />;
  if (error || !internship) {
    return (
      <ErrorState
        title="Internship not found"
        description="Could not load the requested internship posting details."
      />
    );
  }

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
          title={`Edit: ${internship.title}`}
          description={`Update position requirements, eligibility parameters, or deadlines for ${internship.company?.name || "your company"}.`}
        />
      </div>

      <form onSubmit={handleSubmit}>
        <Card className="rounded-2xl border-border/60 shadow-sm space-y-6 p-6">
          <div className="grid gap-6 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="title">Position Title</Label>
              <Input
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                className="rounded-xl"
              />
            </div>

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
          </div>

          <div className="grid gap-6 sm:grid-cols-3">
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

            <div className="space-y-2">
              <Label htmlFor="location">Location</Label>
              <Input
                id="location"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                required
                className="rounded-xl"
              />
            </div>
          </div>

          <div className="grid gap-6 sm:grid-cols-3">
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
                placeholder="Add a skill"
                className="rounded-xl"
              />
              <Button type="button" variant="outline" onClick={handleAddSkill} className="rounded-xl">
                <Plus className="size-4" /> Add
              </Button>
            </div>
          </div>

          <div className="grid gap-6 rounded-xl border border-border/40 bg-muted/20 p-4 sm:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="startDate" className="text-xs font-semibold">Start Date</Label>
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
              <Label htmlFor="endDate" className="text-xs font-semibold">End Date</Label>
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
              <Label htmlFor="deadline" className="text-xs font-semibold">Application Deadline</Label>
              <Input
                id="deadline"
                type="date"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                required
                className="rounded-xl bg-card"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-border/40">
            <Button variant="outline" asChild className="rounded-xl">
              <Link href="/company/internships">Cancel</Link>
            </Button>
            <Button type="submit" disabled={updateInternship.isPending} className="rounded-xl">
              {updateInternship.isPending ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </Card>
      </form>
    </div>
  );
}
