package dev.hoshizora.api.common;

import dev.hoshizora.api.i18n.Lang;
import dev.hoshizora.api.i18n.Term;
import io.swagger.v3.oas.annotations.media.Schema;
import org.jspecify.annotations.Nullable;

@Schema(description = "An organization: an agency, company, armed force, university or international body.")
public record OrganizationRef(
        @Schema(
                description = "Curated slug, or ll2-<Launch Library 2 agency id>; use it with /api/v1/agencies/{key}.",
                example = "jaxa")
        String key,

        String name,
        Lang nameLang,

        @Schema(description = "agency, company, military, academic or international.") @Nullable
        Term type) {}
