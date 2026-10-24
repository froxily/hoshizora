package dev.hoshizora.api.i18n;

import dev.hoshizora.api.web.ApiValue;
import java.util.Locale;

public enum Lang implements ApiValue {
    EN("en", Locale.ENGLISH),
    JA("ja", Locale.JAPANESE);

    private final String value;
    private final Locale locale;

    Lang(String value, Locale locale) {
        this.value = value;
        this.locale = locale;
    }

    public static Lang of(Locale locale) {
        return JA.locale.getLanguage().equals(locale.getLanguage()) ? JA : EN;
    }

    @Override
    public String value() {
        return value;
    }

    public Locale locale() {
        return locale;
    }
}
