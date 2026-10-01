"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAdminExport, useAdminImport } from "@/lib/api/hooks/admin";
import { adminApi } from "@/lib/api/endpoints/admin";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import type { ExportEntity, ImportEntity } from "@/lib/api/types-extra";
import type { Job } from "@/lib/api/types";
import {
  Database,
  Download,
  Upload,
  FileSpreadsheet,
  CheckCircle2,
  AlertCircle,
  FileText,
  Clock,
  Sparkles,
} from "lucide-react";

export default function AdminDataPage() {
  const exportMutation = useAdminExport();
  const importMutation = useAdminImport();

  // Export State
  const [exportEntity, setExportEntity] = useState<ExportEntity>("students");
  const [exportFormat, setExportFormat] = useState<"csv" | "xlsx">("xlsx");
  const [activeExportJob, setActiveExportJob] = useState<Job | null>(null);

  // Import State
  const [importEntity, setImportEntity] = useState<ImportEntity>("students");
  const [importFile, setImportFile] = useState<File | null>(null);
  const [activeImportJob, setActiveImportJob] = useState<Job | null>(null);

  const handleExport = () => {
    exportMutation.mutate(
      { entity: exportEntity, format: exportFormat },
      {
        onSuccess: (res) => {
          toast.success(`Export job queued for ${exportEntity}`);
          setActiveExportJob(res as Job);
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to start export")),
      }
    );
  };

  const handleDownloadTemplate = async () => {
    try {
      const blob = await adminApi.importTemplate(importEntity);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${importEntity}_import_template.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
      toast.success(`Downloaded template for ${importEntity}`);
    } catch (err) {
      toast.error("Failed to download template spreadsheet.");
    }
  };

  const handleImport = (e: React.FormEvent) => {
    e.preventDefault();
    if (!importFile) {
      toast.error("Please select a .csv or .xlsx spreadsheet file to import.");
      return;
    }

    importMutation.mutate(
      { entity: importEntity, file: importFile },
      {
        onSuccess: (res) => {
          toast.success("Import file uploaded and background validation started!");
          setActiveImportJob(res as Job);
          setImportFile(null);
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to submit import")),
      }
    );
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Institutional Data Import & Export"
        description="Bulk import campus cohort rosters, manage company registries, and export complete audit-ready datasets."
      />

      <div className="grid gap-8 lg:grid-cols-2">
        {/* Export Card */}
        <Card className="rounded-2xl border-border/60 shadow-sm p-6 space-y-6">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Download className="size-5 text-primary" />
              <CardTitle className="text-lg">Bulk Data Export</CardTitle>
            </div>
            <CardDescription className="text-xs">
              Generate full database dumps formatted in Excel (.xlsx) or CSV.
            </CardDescription>
          </div>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="expEntity">Dataset Entity</Label>
              <Select value={exportEntity} onValueChange={(v) => setExportEntity(v as ExportEntity)}>
                <SelectTrigger id="expEntity" className="rounded-xl">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="rounded-xl">
                  <SelectItem value="students">Student Cohorts & GPA Profiles</SelectItem>
                  <SelectItem value="companies">Corporate Employer Directory</SelectItem>
                  <SelectItem value="internships">Internship Postings & Requirements</SelectItem>
                  <SelectItem value="applications">Applications & Placement History</SelectItem>
                  <SelectItem value="feedback">Post-Internship Reviews & Ratings</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="expFormat">File Format</Label>
              <Select value={exportFormat} onValueChange={(v) => setExportFormat(v as "csv" | "xlsx")}>
                <SelectTrigger id="expFormat" className="rounded-xl">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="rounded-xl">
                  <SelectItem value="xlsx">Excel Spreadsheet (.xlsx)</SelectItem>
                  <SelectItem value="csv">Comma-Separated Values (.csv)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button
              onClick={handleExport}
              disabled={exportMutation.isPending}
              className="w-full rounded-xl gap-2"
            >
              <FileSpreadsheet className="size-4" />
              {exportMutation.isPending ? "Queuing Export..." : "Generate Dataset Export"}
            </Button>
          </div>

          {activeExportJob && (
            <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 text-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-primary">Job: {activeExportJob.type}</span>
                <Badge variant="outline">{activeExportJob.status}</Badge>
              </div>
              <p className="text-muted-foreground">
                Job ID: <span className="font-mono">{activeExportJob.id}</span>
              </p>
              {activeExportJob.download_url && (
                <Button size="sm" asChild className="rounded-lg text-xs gap-1.5 w-full">
                  <a href={activeExportJob.download_url} target="_blank" rel="noopener noreferrer">
                    <Download className="size-3.5" /> Download Export File
                  </a>
                </Button>
              )}
            </div>
          )}
        </Card>

        {/* Import Card */}
        <Card className="rounded-2xl border-border/60 shadow-sm p-6 space-y-6">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Upload className="size-5 text-primary" />
              <CardTitle className="text-lg">Bulk Data Import</CardTitle>
            </div>
            <CardDescription className="text-xs">
              Upload spreadsheets to provision students, employers, or posting records.
            </CardDescription>
          </div>

          <form onSubmit={handleImport} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="impEntity">Target Entity</Label>
              <Select value={importEntity} onValueChange={(v) => setImportEntity(v as ImportEntity)}>
                <SelectTrigger id="impEntity" className="rounded-xl">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="rounded-xl">
                  <SelectItem value="students">Students Roster</SelectItem>
                  <SelectItem value="companies">Companies Directory</SelectItem>
                  <SelectItem value="internships">Internship Postings</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between p-3 rounded-xl border border-dashed border-border/80 bg-muted/20">
              <div className="space-y-0.5">
                <p className="text-xs font-semibold text-foreground">Standardized Template</p>
                <p className="text-[11px] text-muted-foreground">Download header schema before uploading</p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleDownloadTemplate}
                className="rounded-lg text-xs gap-1"
              >
                <Download className="size-3" /> Template
              </Button>
            </div>

            <div className="space-y-2">
              <Label htmlFor="impFile">Spreadsheet File (.xlsx, .csv)</Label>
              <Input
                id="impFile"
                type="file"
                accept=".xlsx,.csv"
                onChange={(e) => setImportFile(e.target.files?.[0] || null)}
                required
                className="rounded-xl file:mr-2 file:rounded-lg file:border-0 file:bg-primary/10 file:px-2 file:py-1 file:text-xs file:font-semibold file:text-primary"
              />
            </div>

            <Button
              type="submit"
              disabled={importMutation.isPending || !importFile}
              className="w-full rounded-xl gap-2"
            >
              <Upload className="size-4" />
              {importMutation.isPending ? "Validating & Uploading..." : "Process Dataset Import"}
            </Button>
          </form>

          {activeImportJob && (
            <div className="rounded-xl border border-border/60 bg-muted/20 p-4 text-xs space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-foreground">Import Job Results</span>
                <Badge variant="outline">{activeImportJob.status}</Badge>
              </div>

              {activeImportJob.result && (
                <div className="space-y-2">
                  <div className="flex items-center gap-4 text-xs">
                    <span className="text-emerald-600 font-semibold">
                      ✓ Rows Succeeded: {activeImportJob.result.rows_ok ?? 0}
                    </span>
                    <span className="text-rose-600 font-semibold">
                      ✗ Rows Failed: {activeImportJob.result.rows_failed ?? 0}
                    </span>
                  </div>

                  {activeImportJob.result.errors && activeImportJob.result.errors.length > 0 && (
                    <div className="max-h-40 overflow-y-auto space-y-1 bg-card p-2 rounded-lg border border-border/40 font-mono text-[11px]">
                      {activeImportJob.result.errors.map((err, idx) => (
                        <div key={idx} className="text-rose-600">
                          Row {err.row}: [{err.field}] {err.message}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
