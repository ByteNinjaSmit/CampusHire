"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/providers/AuthProvider";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useUpdateMe } from "@/lib/api/hooks/users";
import {
  useMyStudentProfile,
  useUpdateMyStudentProfile,
  useMyFacultyProfile,
  useUpdateMyFacultyProfile,
  useSetDefaultResume,
} from "@/lib/api/hooks/students";
import { useDocuments } from "@/lib/api/hooks/documents";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import { User, GraduationCap, Briefcase, Building2, Shield, Plus, X, FileText, CheckCircle2 } from "lucide-react";
import Link from "next/link";

export default function ProfilePage() {
  const { user } = useAuth();
  const updateMe = useUpdateMe();

  // Basic info form state
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");

  // Student profile state
  const isStudent = user?.role === "STUDENT";
  const { data: studentProfile, isLoading: isStudentLoading } = useMyStudentProfile(isStudent);
  const updateStudentProfile = useUpdateMyStudentProfile();
  const setDefaultResume = useSetDefaultResume();

  const [department, setDepartment] = useState("");
  const [enrollmentNo, setEnrollmentNo] = useState("");
  const [gpa, setGpa] = useState<number | string>("");
  const [graduationYear, setGraduationYear] = useState<number | string>("");
  const [bio, setBio] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [portfolioUrl, setPortfolioUrl] = useState("");
  const [skills, setSkills] = useState<string[]>([]);
  const [newSkill, setNewSkill] = useState("");

  // Faculty profile state
  const isFaculty = user?.role === "FACULTY";
  const { data: facultyProfile, isLoading: isFacultyLoading } = useMyFacultyProfile(isFaculty);
  const updateFacultyProfile = useUpdateMyFacultyProfile();
  const [facultyDept, setFacultyDept] = useState("");
  const [designation, setDesignation] = useState("");
  const [employeeId, setEmployeeId] = useState("");

  // Resumes for student
  const { data: docsData } = useDocuments({ kind: "RESUME", page_size: 20 }, isStudent);
  const resumes = docsData?.items ?? [];

  useEffect(() => {
    if (user) {
      setFullName(user.full_name || "");
      setPhone(user.phone || "");
    }
  }, [user]);

  useEffect(() => {
    if (studentProfile) {
      setDepartment(studentProfile.department || "");
      setEnrollmentNo(studentProfile.enrollment_no || "");
      setGpa(studentProfile.gpa ?? "");
      setGraduationYear(studentProfile.graduation_year ?? "");
      setBio(studentProfile.bio || "");
      setLinkedinUrl(studentProfile.linkedin_url || "");
      setGithubUrl(studentProfile.github_url || "");
      setPortfolioUrl(studentProfile.portfolio_url || "");
      setSkills(studentProfile.skills || []);
    }
  }, [studentProfile]);

  useEffect(() => {
    if (facultyProfile) {
      setFacultyDept(facultyProfile.department || "");
      setDesignation(facultyProfile.designation || "");
      setEmployeeId(facultyProfile.employee_id || "");
    }
  }, [facultyProfile]);

  const handleUpdateBasic = (e: React.FormEvent) => {
    e.preventDefault();
    updateMe.mutate(
      { full_name: fullName, phone: phone || null },
      {
        onSuccess: () => toast.success("Basic details updated successfully"),
        onError: (err) => toast.error(errorMessage(err, "Failed to update profile")),
      }
    );
  };

  const handleUpdateStudent = (e: React.FormEvent) => {
    e.preventDefault();
    updateStudentProfile.mutate(
      {
        department,
        gpa: gpa !== "" ? Number(gpa) : undefined,
        graduation_year: graduationYear !== "" ? Number(graduationYear) : null,
        skills,
        bio: bio || null,
        linkedin_url: linkedinUrl || null,
        github_url: githubUrl || null,
        portfolio_url: portfolioUrl || null,
      },
      {
        onSuccess: () => toast.success("Student profile updated successfully"),
        onError: (err) => toast.error(errorMessage(err, "Failed to update student profile")),
      }
    );
  };

  const handleUpdateFaculty = (e: React.FormEvent) => {
    e.preventDefault();
    updateFacultyProfile.mutate(
      {
        department: facultyDept,
        designation: designation || undefined,
        employee_id: employeeId || undefined,
      },
      {
        onSuccess: () => toast.success("Faculty profile updated successfully"),
        onError: (err) => toast.error(errorMessage(err, "Failed to update faculty profile")),
      }
    );
  };

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

  const handleSetDefaultResume = (docId: string) => {
    setDefaultResume.mutate(docId, {
      onSuccess: () => toast.success("Default resume updated"),
      onError: (err) => toast.error(errorMessage(err, "Failed to set default resume")),
    });
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Profile Settings"
        description="Manage your personal details, academic credentials, and career links."
      />

      <div className="grid gap-6 md:grid-cols-3">
        {/* Profile Card Summary */}
        <Card className="rounded-2xl border-border/60 shadow-sm md:col-span-1">
          <CardHeader className="text-center">
            <div className="mx-auto flex size-20 items-center justify-center rounded-2xl bg-primary/10 text-primary ring-4 ring-primary/20">
              {isStudent && <GraduationCap className="size-10" />}
              {isFaculty && <Briefcase className="size-10" />}
              {user?.role === "COMPANY" && <Building2 className="size-10" />}
              {user?.role === "ADMIN" && <Shield className="size-10" />}
            </div>
            <CardTitle className="mt-3 text-xl">{user?.full_name}</CardTitle>
            <CardDescription className="text-sm">{user?.email}</CardDescription>
            <div className="mt-2 flex justify-center">
              <Badge variant="outline" className="capitalize">
                {user?.role.toLowerCase()}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 border-t pt-4 text-sm text-muted-foreground">
            <div className="flex justify-between">
              <span>Account Status</span>
              <span className="font-medium text-emerald-600 dark:text-emerald-400">Active</span>
            </div>
            <div className="flex justify-between">
              <span>Email Verified</span>
              <span className="font-medium text-foreground">
                {user?.email_verified ? "Verified" : "Pending"}
              </span>
            </div>
            {isStudent && studentProfile?.default_resume && (
              <div className="flex justify-between items-center pt-2">
                <span>Default Resume</span>
                <span className="inline-flex items-center gap-1 text-xs font-medium text-primary">
                  <CheckCircle2 className="size-3.5" /> Attached
                </span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Edit Forms */}
        <div className="space-y-6 md:col-span-2">
          {/* Basic User Information */}
          <Card className="rounded-2xl border-border/60 shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg">Personal Information</CardTitle>
              <CardDescription>Your general identity details across CampusHire.</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleUpdateBasic} className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="fullName">Full Name</Label>
                    <Input
                      id="fullName"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      required
                      className="rounded-xl"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="phone">Phone Number (E.164)</Label>
                    <Input
                      id="phone"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="+1234567890"
                      className="rounded-xl"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email Address</Label>
                  <Input id="email" value={user?.email || ""} disabled className="rounded-xl bg-muted/50" />
                  <p className="text-xs text-muted-foreground">Email address cannot be changed.</p>
                </div>
                <div className="flex justify-end">
                  <Button type="submit" disabled={updateMe.isPending} className="rounded-xl">
                    Save Changes
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {/* Student Profile Specifics */}
          {isStudent && (
            <Card className="rounded-2xl border-border/60 shadow-sm">
              <CardHeader>
                <CardTitle className="text-lg">Academic & Professional Details</CardTitle>
                <CardDescription>
                  Your qualifications, GPA, and skills used for internship applications and eligibility checks.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleUpdateStudent} className="space-y-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="department">Department</Label>
                      <Input
                        id="department"
                        value={department}
                        onChange={(e) => setDepartment(e.target.value)}
                        placeholder="Computer Science"
                        required
                        className="rounded-xl"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="enrollmentNo">Enrollment / Registration No</Label>
                      <Input
                        id="enrollmentNo"
                        value={enrollmentNo}
                        onChange={(e) => setEnrollmentNo(e.target.value)}
                        placeholder="e.g. 2024CS101"
                        className="rounded-xl"
                      />
                    </div>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="gpa">Current GPA (0.00 – 4.00)</Label>
                      <Input
                        id="gpa"
                        type="number"
                        step="0.01"
                        min="0"
                        max="4"
                        value={gpa}
                        onChange={(e) => setGpa(e.target.value)}
                        placeholder="3.85"
                        required
                        className="rounded-xl"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="gradYear">Graduation Year</Label>
                      <Input
                        id="gradYear"
                        type="number"
                        min="2020"
                        max="2035"
                        value={graduationYear}
                        onChange={(e) => setGraduationYear(e.target.value)}
                        placeholder="2026"
                        className="rounded-xl"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="bio">Professional Bio</Label>
                    <Textarea
                      id="bio"
                      value={bio}
                      onChange={(e) => setBio(e.target.value)}
                      placeholder="Brief background, research interests, or career aspirations..."
                      rows={3}
                      className="rounded-xl"
                    />
                  </div>

                  {/* Skills tags */}
                  <div className="space-y-2">
                    <Label>Key Skills</Label>
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
                        placeholder="Add a skill (e.g. Python, React, PostgreSQL)..."
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
                          <button
                            type="button"
                            onClick={() => handleRemoveSkill(s)}
                            className="text-muted-foreground hover:text-foreground"
                          >
                            <X className="size-3" />
                          </button>
                        </Badge>
                      ))}
                    </div>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-3">
                    <div className="space-y-2">
                      <Label htmlFor="linkedin">LinkedIn URL</Label>
                      <Input
                        id="linkedin"
                        type="url"
                        value={linkedinUrl}
                        onChange={(e) => setLinkedinUrl(e.target.value)}
                        placeholder="https://linkedin.com/in/..."
                        className="rounded-xl"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="github">GitHub URL</Label>
                      <Input
                        id="github"
                        type="url"
                        value={githubUrl}
                        onChange={(e) => setGithubUrl(e.target.value)}
                        placeholder="https://github.com/..."
                        className="rounded-xl"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="portfolio">Portfolio URL</Label>
                      <Input
                        id="portfolio"
                        type="url"
                        value={portfolioUrl}
                        onChange={(e) => setPortfolioUrl(e.target.value)}
                        placeholder="https://mywebsite.dev"
                        className="rounded-xl"
                      />
                    </div>
                  </div>

                  <div className="flex justify-end pt-2">
                    <Button type="submit" disabled={updateStudentProfile.isPending} className="rounded-xl">
                      Save Academic Profile
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}

          {/* Default Resume Manager for Student */}
          {isStudent && (
            <Card className="rounded-2xl border-border/60 shadow-sm">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <div>
                  <CardTitle className="text-lg">Default Resume</CardTitle>
                  <CardDescription>
                    Select which resume is pre-selected when applying to internships.
                  </CardDescription>
                </div>
                <Button variant="outline" size="sm" asChild className="rounded-xl">
                  <Link href="/documents">Manage in Documents</Link>
                </Button>
              </CardHeader>
              <CardContent className="space-y-3 pt-2">
                {resumes.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No resumes uploaded yet. Go to{" "}
                    <Link href="/documents" className="text-primary hover:underline">
                      Documents
                    </Link>{" "}
                    to upload your PDF resume.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {resumes.map((doc) => {
                      const isDefault = studentProfile?.default_resume?.id === doc.id;
                      return (
                        <div
                          key={doc.id}
                          className={`flex items-center justify-between rounded-xl border p-3 transition-colors ${
                            isDefault ? "border-primary/40 bg-primary/5" : "bg-card"
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <FileText className="size-5 text-primary" />
                            <div>
                              <p className="text-sm font-medium">{doc.filename}</p>
                              <p className="text-xs text-muted-foreground">
                                {(doc.size_bytes / (1024 * 1024)).toFixed(2)} MB • Status: {doc.verification_status}
                              </p>
                            </div>
                          </div>
                          <div>
                            {isDefault ? (
                              <Badge variant="default" className="text-xs">
                                Default
                              </Badge>
                            ) : (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleSetDefaultResume(doc.id)}
                                disabled={setDefaultResume.isPending}
                                className="rounded-lg text-xs"
                              >
                                Set as default
                              </Button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Faculty Profile Specifics */}
          {isFaculty && (
            <Card className="rounded-2xl border-border/60 shadow-sm">
              <CardHeader>
                <CardTitle className="text-lg">Faculty Information</CardTitle>
                <CardDescription>Department and institutional affiliation details.</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleUpdateFaculty} className="space-y-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="fDept">Department</Label>
                      <Input
                        id="fDept"
                        value={facultyDept}
                        onChange={(e) => setFacultyDept(e.target.value)}
                        placeholder="Computer Science & Engineering"
                        required
                        className="rounded-xl"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="designation">Designation</Label>
                      <Input
                        id="designation"
                        value={designation}
                        onChange={(e) => setDesignation(e.target.value)}
                        placeholder="Associate Professor"
                        className="rounded-xl"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="empId">Employee ID</Label>
                    <Input
                      id="empId"
                      value={employeeId}
                      onChange={(e) => setEmployeeId(e.target.value)}
                      placeholder="FAC-9021"
                      className="rounded-xl"
                    />
                  </div>
                  <div className="flex justify-end">
                    <Button type="submit" disabled={updateFacultyProfile.isPending} className="rounded-xl">
                      Save Faculty Profile
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
