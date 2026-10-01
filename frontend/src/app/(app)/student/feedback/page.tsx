"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { RatingInput, RatingDisplay } from "@/components/shared/Rating";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingTableSkeleton } from "@/components/shared/LoadingSkeletons";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useStudentFeedback, useCompanyFeedback, useCreateStudentFeedback } from "@/lib/api/hooks/feedback";
import { useApplications } from "@/lib/api/hooks/applications";
import { formatRelativeDate, formatDate } from "@/lib/format";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import { MessageSquareText, Star, Building2, Send, CheckCircle2 } from "lucide-react";

export default function StudentFeedbackPage() {
  const [tab, setTab] = useState<"pending" | "submitted" | "received">("pending");

  // Submitted feedback
  const { data: myFeedbackData, isLoading: isMyFeedbackLoading } = useStudentFeedback({ page: 1, page_size: 50 });
  // Received feedback from companies
  const { data: companyFeedbackData, isLoading: isCompanyFeedbackLoading } = useCompanyFeedback({ page: 1, page_size: 50 });
  // Applications to find completed / accepted internships to give feedback for
  const { data: appsData } = useApplications({ page_size: 50 });

  const createFeedback = useCreateStudentFeedback();

  // Form State for new student feedback
  const [selectedAppId, setSelectedAppId] = useState<string>("");
  const [learningRating, setLearningRating] = useState<number>(5);
  const [mentorshipRating, setMentorshipRating] = useState<number>(5);
  const [workEnvRating, setWorkEnvRating] = useState<number>(5);
  const [stipendRating, setStipendRating] = useState<number>(5);
  const [overallRating, setOverallRating] = useState<number>(5);
  const [review, setReview] = useState("");

  const submittedList = myFeedbackData?.items ?? [];
  const receivedList = companyFeedbackData?.items ?? [];
  const submittedAppIds = new Set(submittedList.map((f) => f.application_id));

  // Eligible applications are ACCEPTED applications not yet reviewed
  const eligibleApps = (appsData?.items ?? []).filter(
    (app) => app.status === "ACCEPTED" && !submittedAppIds.has(app.id)
  );

  const handleSubmitFeedback = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAppId) {
      toast.error("Please select an internship to review.");
      return;
    }
    if (!review.trim()) {
      toast.error("Please provide written feedback comments.");
      return;
    }

    createFeedback.mutate(
      {
        application_id: selectedAppId,
        technical_learning: learningRating,
        mentorship: mentorshipRating,
        work_environment: workEnvRating,
        company_culture: stipendRating,
        overall: overallRating,
        comments: review.trim(),
      },
      {
        onSuccess: () => {
          toast.success("Thank you! Your feedback has been recorded.");
          setSelectedAppId("");
          setReview("");
          setTab("submitted");
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to submit feedback")),
      }
    );
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Feedback Center"
        description="Share your post-internship experience and review evaluations shared by employer mentors."
      />

      <Tabs value={tab} onValueChange={(v) => setTab(v as "pending" | "submitted" | "received")}>
        <TabsList className="bg-muted/60">
          <TabsTrigger value="pending">Submit Feedback</TabsTrigger>
          <TabsTrigger value="submitted">My Reviews ({submittedList.length})</TabsTrigger>
          <TabsTrigger value="received">Employer Feedback ({receivedList.length})</TabsTrigger>
        </TabsList>

        {/* Tab 1: Submit Feedback Form */}
        <TabsContent value="pending" className="pt-4">
          <Card className="rounded-2xl border-border/60 shadow-sm max-w-2xl">
            <CardHeader>
              <CardTitle className="text-lg">Submit Internship Review</CardTitle>
              <CardDescription>
                Rate your learning, mentorship, and environment to help future students and campus coordinators.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {eligibleApps.length === 0 ? (
                <EmptyState
                  icon={CheckCircle2}
                  title="No pending reviews"
                  description="You can submit post-internship feedback once an application is accepted and the internship concludes."
                />
              ) : (
                <form onSubmit={handleSubmitFeedback} className="space-y-6">
                  <div className="space-y-2">
                    <Label htmlFor="appSelect">Select Internship</Label>
                    <Select value={selectedAppId} onValueChange={setSelectedAppId}>
                      <SelectTrigger id="appSelect" className="rounded-xl">
                        <SelectValue placeholder="Choose an internship to review" />
                      </SelectTrigger>
                      <SelectContent className="rounded-xl">
                        {eligibleApps.map((app) => (
                          <SelectItem key={app.id} value={app.id}>
                            {app.internship?.title} ({app.internship?.company_name})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-4 rounded-xl border border-border/60 bg-muted/20 p-4">
                    <h4 className="font-semibold text-xs uppercase tracking-wider text-muted-foreground">
                      Experience Ratings (1 – 5 Stars)
                    </h4>

                    <div className="flex items-center justify-between">
                      <span className="text-sm">Learning Experience</span>
                      <RatingInput value={learningRating} onChange={setLearningRating} />
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-sm">Mentorship & Guidance</span>
                      <RatingInput value={mentorshipRating} onChange={setMentorshipRating} />
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-sm">Workplace Culture & Environment</span>
                      <RatingInput value={workEnvRating} onChange={setWorkEnvRating} />
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-sm">Stipend & Compensation Fairness</span>
                      <RatingInput value={stipendRating} onChange={setStipendRating} />
                    </div>

                    <div className="flex items-center justify-between border-t pt-3 font-medium">
                      <span className="text-sm">Overall Experience</span>
                      <RatingInput value={overallRating} onChange={setOverallRating} />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="review">Written Comments & Advice</Label>
                    <Textarea
                      id="review"
                      value={review}
                      onChange={(e) => setReview(e.target.value)}
                      placeholder="Describe your day-to-day work, team support, challenges, and tips for future interns..."
                      rows={4}
                      required
                      className="rounded-xl"
                    />
                  </div>

                  <div className="flex justify-end pt-2">
                    <Button type="submit" disabled={createFeedback.isPending} className="gap-2 rounded-xl">
                      <Send className="size-4" />
                      {createFeedback.isPending ? "Submitting..." : "Submit Review"}
                    </Button>
                  </div>
                </form>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 2: My Submitted Reviews */}
        <TabsContent value="submitted" className="pt-4">
          {isMyFeedbackLoading ? (
            <LoadingTableSkeleton rows={3} />
          ) : submittedList.length === 0 ? (
            <EmptyState
              icon={MessageSquareText}
              title="No submitted reviews"
              description="Reviews you submit after completing internships will appear here."
            />
          ) : (
            <div className="space-y-4 max-w-3xl">
              {submittedList.map((fb) => (
                <Card key={fb.id} className="rounded-2xl border-border/60 shadow-sm p-5 space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-semibold text-base text-foreground">
                        {fb.internship?.title || "Internship"}
                      </h4>
                      <p className="text-xs text-muted-foreground">{fb.company?.name}</p>
                    </div>
                    <RatingDisplay value={fb.overall} size="sm" showValue />
                  </div>

                  {fb.comments && (
                    <p className="text-sm text-foreground/90 whitespace-pre-line leading-relaxed bg-muted/20 p-3 rounded-xl">
                      &ldquo;{fb.comments}&rdquo;
                    </p>
                  )}

                  <div className="flex items-center justify-between text-xs text-muted-foreground pt-1">
                    <span>Submitted {formatDate(fb.created_at)}</span>
                    {fb.response_body && (
                      <span className="text-primary font-medium">Company responded</span>
                    )}
                  </div>

                  {fb.response_body && (
                    <div className="rounded-xl border border-primary/20 bg-primary/5 p-3.5 space-y-1 text-xs">
                      <span className="font-semibold text-primary">Response from Employer:</span>
                      <p className="text-muted-foreground leading-relaxed">{fb.response_body}</p>
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Tab 3: Employer Feedback Received */}
        <TabsContent value="received" className="pt-4">
          {isCompanyFeedbackLoading ? (
            <LoadingTableSkeleton rows={3} />
          ) : receivedList.length === 0 ? (
            <EmptyState
              icon={Star}
              title="No employer feedback yet"
              description="When company supervisors submit evaluations and endorsements for your internship, they will appear here."
            />
          ) : (
            <div className="space-y-4 max-w-3xl">
              {receivedList.map((cf) => (
                <Card key={cf.id} className="rounded-2xl border-border/60 shadow-sm p-5 space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-semibold text-base text-foreground">
                        {cf.internship?.title || "Employer Evaluation"}
                      </h4>
                      <p className="text-xs text-muted-foreground">Evaluator: {cf.author_name || "Manager"}</p>
                    </div>
                    <RatingDisplay value={cf.average} size="sm" showValue />
                  </div>

                  {cf.strengths && (
                    <p className="text-sm text-foreground/90 whitespace-pre-line leading-relaxed bg-muted/20 p-3 rounded-xl">
                      &ldquo;{cf.strengths}&rdquo;
                    </p>
                  )}

                  <div className="flex justify-between text-xs text-muted-foreground pt-1">
                    <span>Recorded {formatDate(cf.created_at)}</span>
                    {cf.hire_likelihood && (
                      <span className="font-medium text-emerald-600 dark:text-emerald-400">
                        Hire Likelihood: {cf.hire_likelihood} / 5
                      </span>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
