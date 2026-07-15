import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDateTime } from "@/lib/utils";

type AuditRow = {
  id: number;
  tenant_id: string | null;
  actor: string | null;
  action: string;
  target: string | null;
  ip: string | null;
  created_at: string;
};

export default function Audit() {
  const { t } = useTranslation();
  const { data: rows = [], isLoading } = useQuery<AuditRow[]>({
    queryKey: ["audit"],
    queryFn: async () => (await api.get<AuditRow[]>("/audit", { params: { limit: 200 } })).data,
  });

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">{t("audit.title")}</h1>
      <Card>
        <CardHeader>
          <CardTitle>{rows.length} entries</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && <p>{t("common.loading")}</p>}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("audit.timestamp")}</TableHead>
                <TableHead>{t("audit.action")}</TableHead>
                <TableHead>{t("audit.target")}</TableHead>
                <TableHead>{t("audit.actor")}</TableHead>
                <TableHead>IP</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="text-xs text-muted-foreground">{formatDateTime(r.created_at)}</TableCell>
                  <TableCell><code className="text-xs">{r.action}</code></TableCell>
                  <TableCell className="font-mono text-xs">{r.target}</TableCell>
                  <TableCell>{r.actor}</TableCell>
                  <TableCell className="text-xs">{r.ip}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
