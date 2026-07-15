import { useTranslation } from "react-i18next";
import { useHealth } from "@/lib/queries";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";

export default function Settings() {
  const { t } = useTranslation();
  const { data: health } = useHealth();

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">{t("settings.title")}</h1>
      <div className="grid gap-4">
        <Card>
          <CardHeader>
            <CardTitle>{t("settings.language")}</CardTitle>
          </CardHeader>
          <CardContent>
            <LanguageSwitcher />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>{t("settings.storage")}</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs bg-muted p-4 rounded-md overflow-auto">
              {JSON.stringify(health?.storage ?? {}, null, 2)}
            </pre>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>{t("settings.version")}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="font-mono">{health?.version ?? "—"}</p>
            <p className="text-xs text-muted-foreground mt-1">License: AGPL-3.0-or-later</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
