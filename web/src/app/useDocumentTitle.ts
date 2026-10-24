import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';

export function useDocumentTitle(page?: string): void {
  const { t } = useTranslation();
  const title = page === undefined ? t('meta.title') : t('meta.pageTitle', { page });
  useEffect(() => {
    document.title = title;
  }, [title]);
}
