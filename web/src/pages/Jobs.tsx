import { useTranslation } from "react-i18next";
import { useJobs } from "@/lib/queries";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDateTime } from "@/lib/utils";

const PHASE_VARIANTS: Record<string, "success" | "warning" | "destructive" | "secondary" | "info" | "default"> = {
  complete: "success",
  failed: "destructive",
  cancelled: "secondary",
  discovery: "info",
  full: "warning",
  delta: "info",
  verify: "info",
};

export default function Jobs() {
  const { t } = useTranslation();
  const { data: jobs = [], isLoading } = useJobs();

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">{t("jobs.title")}</h1>
      <Card>
        <CardHeader>
          <CardTitle>{jobs.length} job(s)</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && <p>{t("common.loading")}</p>}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("jobs.type")}</TableHead>
                <TableHead>{t("jobs.phase")}</TableHead>
                <TableHead>{t("jobs.progress")}</TableHead>
                <TableHead>{t("jobs.errors")}</TableHead>
                <TableHead>{t("jobs.started")}</TableHead>
                <TableHead>{t("jobs.finished")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {jobs.map((j) => (
                <TableRow key={j.id}>
                  <TableCell><Badge variant="outline">{j.job_type}</Badge></TableCell>
                  <TableCell>
                    <Badge variant={PHASE_VARIANTS[j.phase] ?? "default"}>{j.phase}</Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {j.processed} / {j.total_items}
                  </TableCell>
                  <TableCell className={j.errors > 0 ? "text-destructive" : ""}>{j.errors}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{formatDateTime(j.started_at)}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{formatDateTime(j.finished_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
