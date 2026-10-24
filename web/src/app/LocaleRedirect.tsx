import { Navigate, useLocation } from 'react-router';
import { localizePath } from '../i18n/locales';
import { preferredLocale } from '../i18n/preference';

export function LocaleRedirect() {
  const { pathname, search, hash } = useLocation();
  return (
    <Navigate replace to={{ pathname: localizePath(pathname, preferredLocale()), search, hash }} />
  );
}
