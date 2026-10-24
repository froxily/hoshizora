package dev.hoshizora.api.common;

import dev.hoshizora.api.i18n.Bilingual;
import org.jspecify.annotations.Nullable;

public record OrganizationRow(
        String key, Bilingual name, @Nullable String type) {}
