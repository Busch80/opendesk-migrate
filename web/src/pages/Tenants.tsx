import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useTenants } from "@/lib/queries";
import { api, type Tenant } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDateTime } from "@/lib/utils";
import { Plus } from "lucide-react";

export default function Tenants() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: tenants = [], isLoading } = useTenants();

  const createMutation = useMutation({
    mutationFn: async (formData: Omit<Tenant, "id" | "created_at" | "updated_at" | "status">) =>
      (await api.post<Tenant>("/tenants", formData)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tenants"] }),
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">{t("tenants.title")}</h1>
        <Button onClick={() => {
          const code = prompt("Code (lowercase, e.g. 'acme'):"); if (!code) return;
          const name = prompt("Display name:"); if (!name) return;
          createMutation.mutate({ code, display_name: name, opendesk_base_url: null, m365_tenant_id: null });
        }}>
          <Plus className="w-4 h-4 mr-2" />
          {t("tenants.new")}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{tenants.length} tenant(s)</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && <p>{t("common.loading")}</p>}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("tenants.code")}</TableHead>
                <TableHead>{t("tenants.name")}</TableHead>
                <TableHead>{t("tenants.status")}</TableHead>
                <TableHead>{t("tenants.created")}</TableHead>
                <TableHead>{t("tenants.actions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tenants.map((tn) => (
                <TableRow key={tn.id}>
                  <TableCell className="font-mono text-xs">{tn.code}</TableCell>
                  <TableCell>{tn.display_name}</TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        tn.status === "active" ? "success" : tn.status === "archived" ? "outline" : "secondary"
                      }
                    >
                      {tn.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {formatDateTime(tn.created_at)}
                  </TableCell>
                  <TableCell>
                    <Button variant="outline" size="sm" asChild>
                      <Link to={`/tenants/${tn.id}`}>Open</Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
