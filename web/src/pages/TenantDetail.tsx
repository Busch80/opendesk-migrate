import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useTenant } from "@/lib/queries";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function TenantDetail() {
  const { tenantId } = useParams<{ tenantId: string }>();
  const { t } = useTranslation();
  const { data: tenant, isLoading, error } = useTenant(tenantId);

  if (isLoading) return <p>{t("common.loading")}</p>;
  if (error || !tenant) return <p className="text-destructive">{t("common.error")}</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">{tenant.display_name}</h1>
          <p className="text-muted-foreground font-mono text-sm mt-1">{tenant.code}</p>
        </div>
        <Badge variant={tenant.status === "active" ? "success" : "secondary"}>{tenant.status}</Badge>
      </div>

      <div className="grid gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Connections</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">openDesk URL</span>
              <span className="font-mono">{tenant.opendesk_base_url ?? "—"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">M365 Tenant ID</span>
              <span className="font-mono">{tenant.m365_tenant_id ?? "—"}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("tenant_detail.users")}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">No users loaded. Add via API or CSV import.</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
