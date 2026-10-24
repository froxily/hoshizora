package dev.hoshizora.api.i18n;

import org.jspecify.annotations.Nullable;

public record Bilingual(String en, @Nullable String ja) {

    public Text in(Lang lang) {
        return lang == Lang.JA && ja != null ? new Text(ja, Lang.JA) : new Text(en, Lang.EN);
    }

    public static @Nullable Text in(@Nullable String en, @Nullable String ja, Lang lang) {
        return en == null ? null : new Bilingual(en, ja).in(lang);
    }
}
