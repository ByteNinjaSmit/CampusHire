"use client";

import { useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/shared/PageHeader";
import { SearchInput } from "@/components/shared/SearchInput";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingCardGrid } from "@/components/shared/LoadingSkeletons";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useCompanies, useCreateCompany } from "@/lib/api/hooks/companies";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import {
  Building2,
  Plus,
  MapPin,
  ExternalLink,
  Globe,
  Briefcase,
  Users,
  CheckCircle2,
} from "lucide-react";

export default function FacultyCompaniesPage() {
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);

  const { data, isLoading, refetch } = useCompanies({
    q: search || undefined,
    page: 1,
    page_size: 50,
  });

  const createCompany = useCreateCompany();

  // Form states
  const [name, setName] = useState("");
  const [location, setLocation] = useState("");
  const [industry, setIndustry] = useState("");
  const [website, setWebsite] = useState("");
  const [registrationNo, setRegistrationNo] = useState("");
  const [description, setDescription] = useState("");

  const companies = data?.items ?? [];

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !location.trim() || !registrationNo.trim()) {
      toast.error("Please fill in company name, location, and registration number.");
      return;
    }

    createCompany.mutate(
      {
        name: name.trim(),
        location: location.trim(),
        registration_number: registrationNo.trim(),
        industry: industry.trim() || undefined,
        website: website.trim() || undefined,
        description: description.trim() || undefined,
      },
      {
        onSuccess: () => {
          toast.success("Corporate partner registered successfully");
          setCreateOpen(false);
          setName("");
          setLocation("");
          setRegistrationNo("");
          setIndustry("");
          setWebsite("");
          setDescription("");
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to register company")),
      }
    );
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="Corporate Partners"
          description="Browse campus recruitment partners, view company ratings, or register new recruiting organizations."
        />
        <Button onClick={() => setCreateOpen(true)} className="gap-2 rounded-xl">
          <Plus className="size-4" /> Add Corporate Partner
        </Button>
      </div>

      <div className="flex items-center justify-between">
        <div className="w-full sm:w-80">
          <SearchInput value={search} onChange={setSearch} placeholder="Search by name, location, or industry..." />
        </div>
      </div>

      {isLoading ? (
        <LoadingCardGrid count={6} />
      ) : companies.length === 0 ? (
        <EmptyState
          icon={Building2}
          title="No companies found"
          description="Register a corporate partner or clear your search query to see participating organizations."
        />
      ) : (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {companies.map((c) => (
            <Card
              key={c.id}
              className="flex flex-col justify-between rounded-2xl border-border/60 bg-card p-5 shadow-sm transition-all hover:border-primary/40 hover:shadow-md"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary font-bold text-lg shadow-xs">
                    {c.name?.[0]?.toUpperCase() || <Building2 className="size-6" />}
                  </div>
                  <Badge
                    variant={c.status === "ACTIVE" ? "default" : "secondary"}
                    className="text-[10px] capitalize"
                  >
                    {c.status.toLowerCase()}
                  </Badge>
                </div>

                <div>
                  <h3 className="font-semibold text-base text-foreground line-clamp-1 hover:text-primary">
                    <Link href={`/companies/${c.id}`}>{c.name}</Link>
                  </h3>
                  {c.industry && (
                    <span className="text-xs text-muted-foreground">{c.industry}</span>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground pt-1">
                  {c.location && (
                    <span className="flex items-center gap-1">
                      <MapPin className="size-3.5" /> {c.location}
                    </span>
                  )}
                </div>

                {c.description && (
                  <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                    {c.description}
                  </p>
                )}
              </div>

              <div className="flex items-center justify-between border-t pt-3 text-xs">
                {c.website ? (
                  <a
                    href={c.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-primary hover:underline text-xs"
                  >
                    <Globe className="size-3.5" /> Website
                  </a>
                ) : (
                  <span />
                )}

                <Button size="sm" variant="outline" asChild className="rounded-xl text-xs gap-1">
                  <Link href={`/companies/${c.id}`}>View Profile</Link>
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Add Company Modal */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-md rounded-2xl p-6">
          <DialogHeader>
            <DialogTitle>Register Corporate Partner</DialogTitle>
            <DialogDescription>
              Add a new hiring partner organization to the campus placement network.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreate} className="space-y-4 pt-2">
            <div className="space-y-2">
              <Label htmlFor="cName">Company Legal Name</Label>
              <Input
                id="cName"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Acme Technologies Inc."
                required
                className="rounded-xl"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label htmlFor="cLoc">Headquarters / Location</Label>
                <Input
                  id="cLoc"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="Bangalore, India"
                  required
                  className="rounded-xl"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="cReg">Registration Number</Label>
                <Input
                  id="cReg"
                  value={registrationNo}
                  onChange={(e) => setRegistrationNo(e.target.value)}
                  placeholder="CIN / Corp ID"
                  required
                  className="rounded-xl"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label htmlFor="cInd">Industry</Label>
                <Input
                  id="cInd"
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  placeholder="Software / AI"
                  className="rounded-xl"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="cWeb">Website URL</Label>
                <Input
                  id="cWeb"
                  type="url"
                  value={website}
                  onChange={(e) => setWebsite(e.target.value)}
                  placeholder="https://acme.com"
                  className="rounded-xl"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="cDesc">Company Overview</Label>
              <Textarea
                id="cDesc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief description of the organization and technology stack..."
                rows={3}
                className="rounded-xl"
              />
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setCreateOpen(false)} className="rounded-xl">
                Cancel
              </Button>
              <Button type="submit" disabled={createCompany.isPending} className="rounded-xl">
                Register Company
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
