package dev.hoshizora.api.common;

import dev.hoshizora.api.i18n.Bilingual;
import dev.hoshizora.api.i18n.Lang;
import dev.hoshizora.api.i18n.Vocabulary;
import org.jspecify.annotations.Nullable;
import org.springframework.stereotype.Component;

@Component
public final class Refs {

    private final Vocabulary vocabulary;

    Refs(Vocabulary vocabulary) {
        this.vocabulary = vocabulary;
    }

    public OrganizationRef organization(OrganizationRow row, Lang lang) {
        var name = row.name().in(lang);
        var type = row.type() == null ? null : vocabulary.term("organization_type", row.type(), lang);
        return new OrganizationRef(row.key(), name.value(), name.lang(), type);
    }

    public @Nullable CountryRef country(@Nullable String code, @Nullable String en, @Nullable String ja, Lang lang) {
        return code == null || en == null
                ? null
                : new CountryRef(code, new Bilingual(en, ja).in(lang).value());
    }

    public ProgramRef program(String slug, Bilingual name, Lang lang) {
        return new ProgramRef(slug, name.in(lang).value());
    }
}
