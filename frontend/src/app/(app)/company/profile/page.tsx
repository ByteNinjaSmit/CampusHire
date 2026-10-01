"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/shared/PageHeader";
import { LoadingCardGrid } from "@/components/shared/LoadingSkeletons";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/providers/AuthProvider";
import { useCompany, useUpdateCompany } from "@/lib/api/hooks/companies";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import {
  Building2,
  Globe,
  Mail,
  Phone,
  MapPin,
  ExternalLink,
  ShieldCheck,
  Star,
} from "lucide-react";

export default function CompanyProfilePage() {
  const { user } = useAuth();
  const companyId = user?.company?.company_id;

  const { data: company, isLoading, refetch } = useCompany(companyId);
  const updateCompany = useUpdateCompany();

  const [name, setName] = useState("");
  const [regNo, setRegNo] = useState("");
  const [industry, setIndustry] = useState("");
  const [location, setLocation] = useState("");
  const [website, setWebsite] = useState("");
  const [description, setDescription] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactPhone, setContactPhone] = useState("");

  useEffect(() => {
    if (company) {
      setName(company.name || "");
      setRegNo(company.registration_number || "");
      setIndustry(company.industry || "");
      setLocation(company.location || "");
      setWebsite(company.website || "");
      setDescription(company.description || "");
      setContactName(company.contact_person_name || "");
      setContactEmail(company.contact_email || "");
      setContactPhone(company.contact_phone || "");
    }
  }, [company]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyId) return;

    updateCompany.mutate(
      {
        id: companyId,
        body: {
          name: name.trim(),
          registration_number: regNo.trim(),
          industry: industry.trim() || undefined,
          location: location.trim(),
          website: website.trim() || undefined,
          description: description.trim() || undefined,
          contact_person_name: contactName.trim(),
          contact_email: contactEmail.trim(),
          contact_phone: contactPhone.trim() || undefined,
        },
      },
      {
        onSuccess: () => {
          toast.success("Company profile updated successfully");
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to update company profile")),
      }
    );
  };

  if (!companyId) {
    return (
      <EmptyState
        icon={Building2}
        title="No Company Linked"
        description="Your user account is not currently associated with a registered company entity."
      />
    );
  }

  if (isLoading) return <LoadingCardGrid count={2} />;

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <PageHeader
            title="Company Profile"
            description="Manage corporate details, contact representatives, and branding presented to students."
          />
        </div>

        <Button asChild variant="outline" className="gap-2 rounded-xl">
          <Link href={`/companies/${companyId}`} target="_blank">
            <ExternalLink className="size-4" /> View Public Profile
          </Link>
        </Button>
      </div>

      {company && (
        <div className="flex items-center gap-4 p-4 rounded-2xl border border-border/60 bg-card shadow-xs">
          <div className="flex size-14 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary font-bold text-xl shadow-xs">
            {company.name?.[0]?.toUpperCase() || <Building2 className="size-7" />}
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-foreground">{company.name}</h2>
              <Badge variant="outline" className="text-xs text-emerald-600 bg-emerald-500/10 border-emerald-500/20">
                <ShieldCheck className="size-3 mr-1" /> {company.status}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground flex items-center gap-3">
              <span>CIN: {company.registration_number}</span>
              <span>•</span>
              <span className="flex items-center gap-1 text-amber-600 font-semibold">
                <Star className="size-3 fill-current" /> {company.avg_rating?.toFixed(1) || "5.0"} ({company.rating_count || 0} reviews)
              </span>
            </p>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <Card className="rounded-2xl border-border/60 shadow-sm space-y-6 p-6">
          <div className="grid gap-6 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="cName">Company Name</Label>
              <Input
                id="cName"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="rounded-xl"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="cReg">Registration / CIN</Label>
              <Input
                id="cReg"
                value={regNo}
                onChange={(e) => setRegNo(e.target.value)}
                required
                className="rounded-xl font-mono text-xs"
              />
            </div>
          </div>

          <div className="grid gap-6 sm:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="cIndustry">Industry</Label>
              <Input
                id="cIndustry"
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                placeholder="e.g. Technology / FinTech"
                className="rounded-xl"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="cLocation">Headquarters Location</Label>
              <Input
                id="cLocation"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                required
                className="rounded-xl"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="cWebsite">Corporate Website</Label>
              <Input
                id="cWebsite"
                type="url"
                value={website}
                onChange={(e) => setWebsite(e.target.value)}
                placeholder="https://example.com"
                className="rounded-xl"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="cDesc">About Company</Label>
            <Textarea
              id="cDesc"
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe your organization, mission, engineering culture, and work environment..."
              className="rounded-xl"
            />
          </div>

          <div className="border-t border-border/40 pt-4 space-y-4">
            <h3 className="text-sm font-semibold text-foreground">Primary Contact Representative</h3>

            <div className="grid gap-6 sm:grid-cols-3">
              <div className="space-y-2">
                <Label htmlFor="contactName">Representative Name</Label>
                <Input
                  id="contactName"
                  value={contactName}
                  onChange={(e) => setContactName(e.target.value)}
                  required
                  className="rounded-xl"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="contactEmail">Contact Email</Label>
                <Input
                  id="contactEmail"
                  type="email"
                  value={contactEmail}
                  onChange={(e) => setContactEmail(e.target.value)}
                  required
                  className="rounded-xl"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="contactPhone">Contact Phone</Label>
                <Input
                  id="contactPhone"
                  value={contactPhone}
                  onChange={(e) => setContactPhone(e.target.value)}
                  placeholder="+91..."
                  className="rounded-xl"
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-border/40">
            <Button type="submit" disabled={updateCompany.isPending} className="rounded-xl">
              {updateCompany.isPending ? "Saving..." : "Save Company Profile"}
            </Button>
          </div>
        </Card>
      </form>
    </div>
  );
}
