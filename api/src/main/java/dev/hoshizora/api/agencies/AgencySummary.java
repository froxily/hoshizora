package dev.hoshizora.api.agencies;

import dev.hoshizora.api.common.CountryRef;
import dev.hoshizora.api.common.ProgramRef;
import dev.hoshizora.api.i18n.Lang;
import dev.hoshizora.api.i18n.Term;
import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;
import org.jspecify.annotations.Nullable;

@Schema(description = "An organization with its countries, national programs and launch totals.")
public record AgencySummary(
        @Schema(description = "Curated slug, or ll2-<Launch Library 2 agency id>.", example = "jaxa")
        String key,

        String name,
        Lang nameLang,
        @Nullable String abbrev,

        @Schema(description = "agency, company, military, academic or international.") @Nullable
        Term type,

        List<CountryRef> countries,
        List<ProgramRef> programs,
        @Nullable Integer foundingYear,

        @Schema(description = "Launches as provider; absent for organizations that never provided one.") @Nullable
        LaunchStats launches) {}
