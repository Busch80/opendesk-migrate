import { useHealth, useTenants, useJobs } from "@/lib/queries";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useTranslation } from "react-i18next";
import { formatBytes } from "@/lib/utils";

export default function Dashboard() {
  const { t } = useTranslation();
  const { data: health } = useHealth();
  const { data: tenants = [] } = useTenants();
  const { data: jobs = [] } = useJobs();

  const activeTenants = tenants.filter((tn) => tn.status === "active").length;
  const runningJobs = jobs.filter((j) =>
    ["discovery", "full", "delta", "verify"].includes(j.phase),
  ).length;

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">{t("dashboard.title")}</h1>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t("dashboard.active_tenants")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{activeTenants}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t("dashboard.running_jobs")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{runningJobs}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t("dashboard.errors_24h")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-destructive">
              {jobs.reduce((sum, j) => sum + j.errors, 0)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t("settings.version")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{health?.version ?? "—"}</div>
            <p className="text-xs text-muted-foreground mt-1">
              DB: <span className="font-mono">{health?.database}</span>
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Storage</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="text-xs bg-muted p-4 rounded-md overflow-auto">
            {JSON.stringify(health?.storage ?? {}, null, 2)}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}
