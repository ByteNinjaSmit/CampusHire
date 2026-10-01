"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useCompany, useCompanyInternships, useCompanyRatings } from "@/lib/api/hooks/companies";
import { useStudentFeedback } from "@/lib/api/hooks/feedback";
import { PageHeader } from "@/components/shared/PageHeader";
import { RatingDisplay } from "@/components/shared/Rating";
import { Chart } from "@/components/shared/Chart";
import { LoadingCardGrid } from "@/components/shared/LoadingSkeletons";
import { ErrorState } from "@/components/shared/ErrorState";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { formatDate, formatCurrency } from "@/lib/format";
import {
  Building2,
  Globe,
  MapPin,
  Briefcase,
  Star,
  Users,
  ExternalLink,
  ArrowRight,
  ArrowLeft,
  Calendar,
} from "lucide-react";

export default function CompanyProfilePage() {
  const params = useParams();
  const id = typeof params?.id === "string" ? params.id : "";

  const { data: company, isLoading, error, refetch } = useCompany(id);
  const { data: internshipsData } = useCompanyInternships(id, { page_size: 20 });
  const { data: ratingsData } = useCompanyRatings(id);
  const { data: feedbackData } = useStudentFeedback({ company_id: id, page_size: 20 });

  if (isLoading) return <LoadingCardGrid count={3} />;
  if (error || !company) return <ErrorState title="Company not found" description="Cannot find the specified company profile." onRetry={() => refetch()} />;

  const internships = internshipsData?.items ?? [];
  const reviews = feedbackData?.items ?? [];

  // Radar chart options for ratings if available
  const radarOption = ratingsData
    ? {
        tooltip: {},
        radar: {
          indicator: [
            { name: "Learning", max: 5 },
            { name: "Mentorship", max: 5 },
            { name: "Work Env", max: 5 },
            { name: "Stipend", max: 5 },
            { name: "Overall", max: 5 },
          ],
          radius: "65%",
        },
        series: [
          {
            name: "Ratings",
            type: "radar",
            data: [
              {
                value: [
                  ratingsData.learning_experience ?? 5,
                  ratingsData.mentorship_quality ?? 5,
                  ratingsData.work_environment ?? 5,
                  ratingsData.stipend_fairness ?? 5,
                  ratingsData.overall_rating ?? 5,
                ],
                name: company.name,
                areaStyle: { opacity: 0.25 },
              },
            ],
          },
        ],
      }
    : null;

  return (
    <div className="space-y-8">
      <div>
        <Link
          href="/internships"
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-3 transition-colors"
        >
          <ArrowLeft className="size-3.5" /> Back to internships
        </Link>
      </div>

      {/* Company Banner & Profile Header */}
      <Card className="overflow-hidden rounded-2xl border-border/60 shadow-sm">
        <div className="h-32 bg-gradient-to-r from-primary/20 via-primary/10 to-indigo-500/20" />
        <CardContent className="relative px-6 pb-6 pt-0">
          <div className="-mt-12 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div className="flex items-end gap-4">
              <div className="flex size-24 shrink-0 items-center justify-center rounded-2xl bg-card text-primary font-bold text-3xl shadow-md ring-4 ring-background">
                {company.name?.[0]?.toUpperCase() || <Building2 className="size-12" />}
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h1 className="text-2xl font-bold text-foreground">{company.name}</h1>
                  <Badge variant="outline" className="capitalize text-xs">{company.status?.toLowerCase()}</Badge>
                </div>
                <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                  {company.industry && <span>{company.industry}</span>}
                  {company.location && (
                    <>
                      <span>•</span>
                      <span className="flex items-center gap-1">
                        <MapPin className="size-3.5" /> {company.location}
                      </span>
                    </>
                  )}
                  {company.website && (
                    <>
                      <span>•</span>
                      <a
                        href={company.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-primary hover:underline"
                      >
                        <Globe className="size-3.5" /> {company.website.replace(/^https?:\/\//, "")}
                      </a>
                    </>
                  )}
                </div>
              </div>
            </div>

            {ratingsData?.overall_rating && (
              <div className="flex items-center gap-2 rounded-xl border bg-muted/30 px-3.5 py-2">
                <Star className="size-5 fill-amber-400 text-amber-400" />
                <span className="text-lg font-bold">{ratingsData.overall_rating.toFixed(1)}</span>
                <span className="text-xs text-muted-foreground">({ratingsData.review_count || 0} reviews)</span>
              </div>
            )}
          </div>

          {company.description && (
            <p className="mt-6 text-sm text-foreground/90 leading-relaxed max-w-3xl">
              {company.description}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Main Grid: Open Internships (2 col) + Rating Breakdown / Radar (1 col) */}
      <div className="grid gap-8 lg:grid-cols-3">
        {/* Open Roles */}
        <div className="space-y-6 lg:col-span-2">
          <Card className="rounded-2xl border-border/60 shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-lg">Active Internship Opportunities</CardTitle>
                <CardDescription>Open roles currently recruiting at this organization.</CardDescription>
              </div>
              <Badge variant="secondary">{internships.length} Openings</Badge>
            </CardHeader>
            <CardContent>
              {internships.length === 0 ? (
                <div className="py-8 text-center text-xs text-muted-foreground">
                  No active internship postings available from this company right now.
                </div>
              ) : (
                <div className="divide-y divide-border/60 rounded-xl border border-border/60">
                  {internships.map((item) => (
                    <div
                      key={item.id}
                      className="flex flex-col gap-3 p-4 transition-colors hover:bg-muted/30 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div className="space-y-1">
                        <h4 className="font-semibold text-sm text-foreground hover:text-primary">
                          <Link href={`/internships/${item.id}`}>{item.title}</Link>
                        </h4>
                        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                          <Badge variant="secondary" className="text-[10px]">
                            {item.work_mode}
                          </Badge>
                          <span>{item.duration_weeks} Weeks</span>
                          <span>•</span>
                          <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                            {item.stipend_monthly ? `${formatCurrency(item.stipend_monthly)} / mo` : "Unpaid"}
                          </span>
                        </div>
                      </div>

                      <Button size="sm" asChild variant="outline" className="rounded-xl text-xs gap-1">
                        <Link href={`/internships/${item.id}`}>
                          View Details <ArrowRight className="size-3.5" />
                        </Link>
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Student Reviews */}
          <Card className="rounded-2xl border-border/60 shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Intern Reviews & Feedback</CardTitle>
              <CardDescription>Experiences shared by previous student interns.</CardDescription>
            </CardHeader>
            <CardContent>
              {reviews.length === 0 ? (
                <p className="text-xs text-muted-foreground py-6 text-center">
                  No reviews posted for this employer yet.
                </p>
              ) : (
                <div className="space-y-4">
                  {reviews.map((r) => (
                    <div key={r.id} className="rounded-xl border p-4 space-y-2 bg-muted/10">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-xs text-foreground">{r.internship_title}</span>
                        <RatingDisplay value={r.overall_rating} size="sm" showValue />
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed italic">
                        &ldquo;{r.review_comments}&rdquo;
                      </p>
                      <span className="text-[11px] text-muted-foreground block pt-1">
                        Reviewed {formatDate(r.created_at)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar: Rating Breakdown & Radar Chart */}
        <div className="space-y-6">
          {radarOption && (
            <Card className="rounded-2xl border-border/60 shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Experience Radar</CardTitle>
                <CardDescription>Assessment across five core dimensions.</CardDescription>
              </CardHeader>
              <CardContent>
                <Chart option={radarOption} height={260} />
              </CardContent>
            </Card>
          )}

          <Card className="rounded-2xl border-border/60 shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Organization Overview</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs text-muted-foreground">
              <div className="flex justify-between">
                <span>Industry</span>
                <span className="font-medium text-foreground">{company.industry || "Technology"}</span>
              </div>
              <div className="flex justify-between">
                <span>Headquarters</span>
                <span className="font-medium text-foreground">{company.location || "Corporate"}</span>
              </div>
              <div className="flex justify-between">
                <span>Corporate Registration</span>
                <span className="font-medium text-foreground">{company.registration_number}</span>
              </div>
              <div className="flex justify-between">
                <span>Total Active Openings</span>
                <span className="font-medium text-foreground">{internships.length}</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
