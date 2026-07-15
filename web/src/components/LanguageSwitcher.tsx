import { useTranslation } from "react-i18next";

export function LanguageSwitcher() {
  const { i18n, t } = useTranslation();
  const locales = ["de", "fr", "it", "en"] as const;
  return (
    <select
      value={i18n.language}
      onChange={(e) => i18n.changeLanguage(e.target.value)}
      className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
      aria-label={t("settings.language")}
    >
      {locales.map((loc) => (
        <option key={loc} value={loc}>
          {t(`languages.${loc}`, { defaultValue: loc.toUpperCase() })}
        </option>
      ))}
    </select>
  );
}
