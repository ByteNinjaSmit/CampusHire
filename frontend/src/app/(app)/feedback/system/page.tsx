"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingTableSkeleton } from "@/components/shared/LoadingSkeletons";
import { useSystemFeedback, useCreateSystemFeedback } from "@/lib/api/hooks/feedback";
import { formatRelativeDate } from "@/lib/format";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import { MessageSquarePlus, LifeBuoy, CheckCircle2, Clock, AlertTriangle, Sparkles } from "lucide-react";
import type { SystemFeedbackCreateRequest } from "@/lib/api/types";

type FeedbackType = SystemFeedbackCreateRequest["type"];

export default function SystemFeedbackPage() {
  const [type, setType] = useState<FeedbackType>("FEATURE");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  const { data, isLoading } = useSystemFeedback({ page: 1, page_size: 50 });
  const createFeedback = useCreateSystemFeedback();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) {
      toast.error("Please fill in both the title and description.");
      return;
    }

    createFeedback.mutate(
      { type, title, description },
      {
        onSuccess: () => {
          toast.success("Feedback submitted. Thank you for helping us improve!");
          setTitle("");
          setDescription("");
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to submit feedback")),
      }
    );
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "RESOLVED":
        return <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">Resolved</Badge>;
      case "PLANNED":
        return <Badge className="bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">Planned</Badge>;
      case "UNDER_REVIEW":
        return <Badge className="bg-sky-500/10 text-sky-600 dark:text-sky-400">Under Review</Badge>;
      case "CLOSED":
        return <Badge variant="secondary">Closed</Badge>;
      default:
        return <Badge variant="outline">New</Badge>;
    }
  };

  const getTypeIcon = (t: string) => {
    switch (t) {
      case "BUG":
        return <AlertTriangle className="size-4 text-rose-500" />;
      case "FEATURE":
      case "FEATURE_REQUEST":
        return <Sparkles className="size-4 text-amber-500" />;
      default:
        return <LifeBuoy className="size-4 text-primary" />;
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Help & Feedback"
        description="Submit bug reports, feature suggestions, or general improvements to make CampusHire better."
      />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Submission Form */}
        <Card className="rounded-2xl border-border/60 shadow-sm lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-lg">Submit Feedback</CardTitle>
            <CardDescription>Tell us what is working or what could be improved.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="category">Feedback Category</Label>
                <Select value={type} onValueChange={(v) => setType(v as FeedbackType)}>
                  <SelectTrigger id="category" className="rounded-xl">
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent className="rounded-xl">
                    <SelectItem value="FEATURE">Feature Request</SelectItem>
                    <SelectItem value="BUG">Bug Report</SelectItem>
                    <SelectItem value="IMPROVEMENT">General Improvement</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="title">Summary / Subject</Label>
                <Input
                  id="title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Add filtering by remote work status"
                  required
                  className="rounded-xl"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Details & Steps to Reproduce</Label>
                <Textarea
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Please provide any details, expected behavior, or screenshots context..."
                  rows={4}
                  required
                  className="rounded-xl"
                />
              </div>

              <Button
                type="submit"
                disabled={createFeedback.isPending}
                className="w-full gap-2 rounded-xl"
              >
                <MessageSquarePlus className="size-4" />
                {createFeedback.isPending ? "Submitting..." : "Send Feedback"}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Previous Feedback List */}
        <Card className="rounded-2xl border-border/60 shadow-sm lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">My Submissions</CardTitle>
            <CardDescription>Track the review and implementation status of your submitted feedback.</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <LoadingTableSkeleton rows={4} />
            ) : !data?.items || data.items.length === 0 ? (
              <EmptyState
                icon={LifeBuoy}
                title="No feedback submissions yet"
                description="Your suggestions and reported issues will be tracked here."
              />
            ) : (
              <div className="space-y-3">
                {data.items.map((item) => (
                  <div
                    key={item.id}
                    className="flex flex-col gap-2 rounded-xl border border-border/60 bg-card p-4 transition-colors hover:bg-muted/30 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        {getTypeIcon(item.type)}
                        <span className="font-medium text-sm text-foreground">{item.title}</span>
                      </div>
                      <p className="text-xs text-muted-foreground line-clamp-2">{item.description}</p>
                      <p className="text-[11px] text-muted-foreground pt-1">
                        Submitted {formatRelativeDate(item.created_at)}
                      </p>
                    </div>

                    <div className="flex items-center gap-2 self-start sm:self-center">
                      {getStatusBadge(item.status)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
