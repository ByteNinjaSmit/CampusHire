"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { SearchInput } from "@/components/shared/SearchInput";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingTableSkeleton } from "@/components/shared/LoadingSkeletons";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  useUsers,
  useCreateUser,
  useActivateUser,
  useDeactivateUser,
  useBulkUsers,
} from "@/lib/api/hooks/users";
import { useCompanies } from "@/lib/api/hooks/companies";
import { formatDate, formatRelativeDate } from "@/lib/format";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import type { Role, UserSummary } from "@/lib/api/types";
import {
  Users,
  UserPlus,
  Shield,
  GraduationCap,
  Briefcase,
  Building2,
  CheckCircle2,
  XCircle,
  MoreVertical,
  Filter,
} from "lucide-react";

export default function AdminUsersPage() {
  const [roleFilter, setRoleFilter] = useState<string>("ALL");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, refetch } = useUsers({
    role: roleFilter !== "ALL" ? (roleFilter as Role) : undefined,
    q: search || undefined,
    page,
    page_size: 20,
  });

  const { data: companiesData } = useCompanies({ page_size: 100 });
  const createUser = useCreateUser();
  const activateUser = useActivateUser();
  const deactivateUser = useDeactivateUser();
  const bulkUsers = useBulkUsers();

  // Create User Dialog State
  const [createOpen, setCreateOpen] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("Password@123");
  const [newFullName, setNewFullName] = useState("");
  const [newPhone, setNewPhone] = useState("+919876543210");
  const [newRole, setNewRole] = useState<Role>("STUDENT");
  const [markVerified, setMarkVerified] = useState(true);

  // Role specific fields
  const [studentDept, setStudentDept] = useState("Computer Science & Engineering");
  const [studentGpa, setStudentGpa] = useState("3.5");
  const [studentEnroll, setStudentEnroll] = useState("");
  const [studentGradYear, setStudentGradYear] = useState("2026");

  const [facultyDept, setFacultyDept] = useState("Computer Science & Engineering");
  const [facultyDesignation, setFacultyDesignation] = useState("Associate Professor");
  const [facultyEmpId, setFacultyEmpId] = useState("");

  const [companyId, setCompanyId] = useState("");
  const [companyTitle, setCompanyTitle] = useState("Talent Acquisition Lead");

  // Deactivate reason dialog
  const [deactivateTarget, setDeactivateTarget] = useState<UserSummary | null>(null);
  const [deactivateReason, setDeactivateReason] = useState("");

  // Bulk selection
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const usersList = data?.items ?? [];

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(usersList.map((u) => u.id));
    } else {
      setSelectedIds([]);
    }
  };

  const handleToggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEmail || !newFullName || !newPassword) {
      toast.error("Please fill in email, password, and full name.");
      return;
    }

    createUser.mutate(
      {
        email: newEmail.trim().toLowerCase(),
        password: newPassword,
        full_name: newFullName.trim(),
        phone: newPhone.trim() || undefined,
        role: newRole,
        mark_verified: markVerified,
        student:
          newRole === "STUDENT"
            ? {
                department: studentDept,
                gpa: Number(studentGpa) || 3.0,
                enrollment_no: studentEnroll.trim() || undefined,
                graduation_year: Number(studentGradYear) || undefined,
              }
            : undefined,
        faculty:
          newRole === "FACULTY"
            ? {
                department: facultyDept,
                designation: facultyDesignation.trim() || undefined,
                employee_id: facultyEmpId.trim() || undefined,
              }
            : undefined,
        company:
          newRole === "COMPANY"
            ? {
                company_id: companyId,
                job_title: companyTitle.trim() || undefined,
              }
            : undefined,
      },
      {
        onSuccess: () => {
          toast.success(`Created user account for ${newFullName}`);
          setCreateOpen(false);
          // reset form
          setNewEmail("");
          setNewFullName("");
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to create user")),
      }
    );
  };

  const handleActivate = (id: string, name: string) => {
    activateUser.mutate(id, {
      onSuccess: () => {
        toast.success(`User ${name} activated`);
        refetch();
      },
      onError: (err) => toast.error(errorMessage(err, "Failed to activate user")),
    });
  };

  const handleDeactivate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!deactivateTarget) return;

    deactivateUser.mutate(
      { id: deactivateTarget.id, reason: deactivateReason || "Administrative deactivation" },
      {
        onSuccess: () => {
          toast.info(`User ${deactivateTarget.full_name} deactivated`);
          setDeactivateTarget(null);
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to deactivate user")),
      }
    );
  };

  const handleBulkAction = (action: "activate" | "deactivate") => {
    if (selectedIds.length === 0) return;
    bulkUsers.mutate(
      { ids: selectedIds, action },
      {
        onSuccess: () => {
          toast.success(`Bulk ${action} applied to ${selectedIds.length} users`);
          setSelectedIds([]);
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Bulk action failed")),
      }
    );
  };

  const companies = companiesData?.items ?? [];

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="User Account Management"
          description="Manage institutional user profiles, issue role access, and monitor verification status."
        />

        <Button onClick={() => setCreateOpen(true)} className="rounded-xl gap-2">
          <UserPlus className="size-4" /> Provision New User
        </Button>
      </div>

      {/* Filters and Search Bar */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-3">
          <Select value={roleFilter} onValueChange={(v) => { setRoleFilter(v); setPage(1); }}>
            <SelectTrigger className="w-40 rounded-xl">
              <SelectValue placeholder="All Roles" />
            </SelectTrigger>
            <SelectContent className="rounded-xl">
              <SelectItem value="ALL">All Roles ({data?.total ?? 0})</SelectItem>
              <SelectItem value="STUDENT">Students</SelectItem>
              <SelectItem value="FACULTY">Faculty</SelectItem>
              <SelectItem value="COMPANY">Companies</SelectItem>
              <SelectItem value="ADMIN">Administrators</SelectItem>
            </SelectContent>
          </Select>

          {selectedIds.length > 0 && (
            <div className="flex items-center gap-2 rounded-xl bg-muted/60 px-3 py-1 text-xs">
              <span className="font-semibold text-foreground">{selectedIds.length} selected</span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => handleBulkAction("activate")}
                className="h-7 text-xs text-emerald-600 hover:text-emerald-700"
              >
                Activate All
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => handleBulkAction("deactivate")}
                className="h-7 text-xs text-rose-600 hover:text-rose-700"
              >
                Deactivate All
              </Button>
            </div>
          )}
        </div>

        <div className="w-full sm:w-72">
          <SearchInput
            value={search}
            onChange={(v) => { setSearch(v); setPage(1); }}
            placeholder="Search name, email..."
          />
        </div>
      </div>

      {/* Users Table */}
      {isLoading ? (
        <LoadingTableSkeleton rows={8} />
      ) : usersList.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No users found"
          description="No user records matched your current query or role filter."
          action={
            <Button onClick={() => setCreateOpen(true)} className="rounded-xl">
              Create New User
            </Button>
          }
        />
      ) : (
        <div className="divide-y divide-border/60 rounded-2xl border border-border/60 bg-card shadow-sm overflow-hidden">
          <div className="flex items-center justify-between p-3.5 bg-muted/30 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            <div className="flex items-center gap-3">
              <Checkbox
                checked={selectedIds.length === usersList.length && usersList.length > 0}
                onCheckedChange={(c) => handleSelectAll(!!c)}
                aria-label="Select all"
              />
              <span>User Details</span>
            </div>
            <div className="flex items-center gap-12 pr-4">
              <span>Role</span>
              <span>Status</span>
              <span>Joined</span>
              <span>Actions</span>
            </div>
          </div>

          {usersList.map((u) => {
            const isSelected = selectedIds.includes(u.id);
            return (
              <div
                key={u.id}
                className={`flex items-center justify-between p-4 transition-colors ${
                  isSelected ? "bg-primary/5" : "hover:bg-muted/20"
                }`}
              >
                <div className="flex items-center gap-3.5">
                  <Checkbox
                    checked={isSelected}
                    onCheckedChange={() => handleToggleSelect(u.id)}
                    aria-label={`Select ${u.full_name}`}
                  />
                  <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary font-bold text-sm">
                    {u.full_name?.[0]?.toUpperCase() || "U"}
                  </div>
                  <div>
                    <h3 className="font-semibold text-sm text-foreground">{u.full_name}</h3>
                    <p className="text-xs text-muted-foreground">{u.email}</p>
                  </div>
                </div>

                <div className="flex items-center gap-8">
                  <Badge
                    variant="outline"
                    className={`text-xs font-semibold ${
                      u.role === "ADMIN"
                        ? "border-purple-500/30 text-purple-600 bg-purple-500/10"
                        : u.role === "FACULTY"
                        ? "border-blue-500/30 text-blue-600 bg-blue-500/10"
                        : u.role === "COMPANY"
                        ? "border-amber-500/30 text-amber-600 bg-amber-500/10"
                        : "border-emerald-500/30 text-emerald-600 bg-emerald-500/10"
                    }`}
                  >
                    {u.role}
                  </Badge>

                  <Badge
                    variant="outline"
                    className={`text-[11px] ${
                      u.is_active
                        ? "border-emerald-500/20 text-emerald-600 bg-emerald-500/10"
                        : "border-rose-500/20 text-rose-600 bg-rose-500/10"
                    }`}
                  >
                    {u.is_active ? "Active" : "Deactivated"}
                  </Badge>

                  <span className="text-xs text-muted-foreground hidden sm:inline">
                    {formatDate(u.created_at)}
                  </span>

                  <div className="flex items-center gap-1.5">
                    {u.is_active ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setDeactivateTarget(u);
                          setDeactivateReason("");
                        }}
                        className="rounded-lg text-xs text-muted-foreground hover:text-destructive h-8"
                      >
                        Deactivate
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleActivate(u.id, u.full_name)}
                        className="rounded-lg text-xs text-emerald-600 h-8"
                      >
                        Activate
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Provision User Modal */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="rounded-2xl sm:max-w-lg max-h-[85vh] overflow-y-auto">
          <form onSubmit={handleCreate}>
            <DialogHeader>
              <DialogTitle>Provision Institutional User</DialogTitle>
              <DialogDescription>
                Create a new user profile with campus credentials and role privileges.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label htmlFor="uName">Full Name</Label>
                  <Input
                    id="uName"
                    value={newFullName}
                    onChange={(e) => setNewFullName(e.target.value)}
                    required
                    className="rounded-xl"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="uRole">Role Assignment</Label>
                  <Select value={newRole} onValueChange={(v) => setNewRole(v as Role)}>
                    <SelectTrigger id="uRole" className="rounded-xl">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="rounded-xl">
                      <SelectItem value="STUDENT">Student</SelectItem>
                      <SelectItem value="FACULTY">Faculty Officer</SelectItem>
                      <SelectItem value="COMPANY">Company Recruiter</SelectItem>
                      <SelectItem value="ADMIN">System Administrator</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label htmlFor="uEmail">Email Address</Label>
                  <Input
                    id="uEmail"
                    type="email"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    required
                    className="rounded-xl"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="uPass">Initial Password</Label>
                  <Input
                    id="uPass"
                    type="text"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    required
                    className="rounded-xl font-mono text-xs"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="uPhone">Phone Number</Label>
                <Input
                  id="uPhone"
                  value={newPhone}
                  onChange={(e) => setNewPhone(e.target.value)}
                  className="rounded-xl"
                />
              </div>

              {/* Dynamic Role Sections */}
              {newRole === "STUDENT" && (
                <div className="p-3.5 rounded-xl border border-border/60 bg-muted/20 space-y-3">
                  <h4 className="text-xs font-semibold uppercase text-muted-foreground">
                    Student Profile Details
                  </h4>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <Label className="text-xs">Department</Label>
                      <Input
                        value={studentDept}
                        onChange={(e) => setStudentDept(e.target.value)}
                        className="rounded-lg h-8 text-xs bg-card"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label className="text-xs">GPA (4.0 Scale)</Label>
                      <Input
                        type="number"
                        step="0.01"
                        value={studentGpa}
                        onChange={(e) => setStudentGpa(e.target.value)}
                        className="rounded-lg h-8 text-xs bg-card"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <Label className="text-xs">Enrollment Number</Label>
                      <Input
                        value={studentEnroll}
                        onChange={(e) => setStudentEnroll(e.target.value)}
                        placeholder="e.g. EN20220914"
                        className="rounded-lg h-8 text-xs bg-card"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label className="text-xs">Graduation Year</Label>
                      <Input
                        type="number"
                        value={studentGradYear}
                        onChange={(e) => setStudentGradYear(e.target.value)}
                        className="rounded-lg h-8 text-xs bg-card"
                      />
                    </div>
                  </div>
                </div>
              )}

              {newRole === "FACULTY" && (
                <div className="p-3.5 rounded-xl border border-border/60 bg-muted/20 space-y-3">
                  <h4 className="text-xs font-semibold uppercase text-muted-foreground">
                    Faculty Officer Details
                  </h4>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <Label className="text-xs">Department</Label>
                      <Input
                        value={facultyDept}
                        onChange={(e) => setFacultyDept(e.target.value)}
                        className="rounded-lg h-8 text-xs bg-card"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label className="text-xs">Designation</Label>
                      <Input
                        value={facultyDesignation}
                        onChange={(e) => setFacultyDesignation(e.target.value)}
                        className="rounded-lg h-8 text-xs bg-card"
                      />
                    </div>
                  </div>
                </div>
              )}

              {newRole === "COMPANY" && (
                <div className="p-3.5 rounded-xl border border-border/60 bg-muted/20 space-y-3">
                  <h4 className="text-xs font-semibold uppercase text-muted-foreground">
                    Company Affiliation
                  </h4>
                  <div className="space-y-1.5">
                    <Label className="text-xs">Associated Corporate Partner</Label>
                    <Select value={companyId} onValueChange={setCompanyId}>
                      <SelectTrigger className="rounded-lg h-8 text-xs bg-card">
                        <SelectValue placeholder="Select Company" />
                      </SelectTrigger>
                      <SelectContent className="rounded-xl">
                        {companies.map((c) => (
                          <SelectItem key={c.id} value={c.id}>
                            {c.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              )}

              <div className="flex items-center gap-2 pt-2">
                <Checkbox
                  id="markVer"
                  checked={markVerified}
                  onCheckedChange={(c) => setMarkVerified(!!c)}
                />
                <Label htmlFor="markVer" className="text-xs font-normal text-muted-foreground">
                  Mark email as pre-verified (skip verification email requirement)
                </Label>
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setCreateOpen(false)} className="rounded-xl">
                Cancel
              </Button>
              <Button type="submit" disabled={createUser.isPending} className="rounded-xl">
                {createUser.isPending ? "Creating..." : "Provision User"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Deactivate User Dialog */}
      <Dialog open={!!deactivateTarget} onOpenChange={(o) => !o && setDeactivateTarget(null)}>
        <DialogContent className="rounded-2xl sm:max-w-md">
          <form onSubmit={handleDeactivate}>
            <DialogHeader>
              <DialogTitle>Deactivate User Account</DialogTitle>
              <DialogDescription>
                Revoke login access for {deactivateTarget?.full_name} ({deactivateTarget?.email}).
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="deactReason">Reason for Deactivation</Label>
                <Input
                  id="deactReason"
                  value={deactivateReason}
                  onChange={(e) => setDeactivateReason(e.target.value)}
                  placeholder="e.g. Graduated, policy violation, or staff departure"
                  required
                  className="rounded-xl"
                />
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDeactivateTarget(null)} className="rounded-xl">
                Cancel
              </Button>
              <Button type="submit" variant="destructive" disabled={deactivateUser.isPending} className="rounded-xl">
                {deactivateUser.isPending ? "Deactivating..." : "Confirm Deactivation"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
