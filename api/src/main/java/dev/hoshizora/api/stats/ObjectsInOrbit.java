package dev.hoshizora.api.stats;

import dev.hoshizora.api.common.CountryRef;
import dev.hoshizora.api.common.OrganizationRef;
import dev.hoshizora.api.i18n.Lang;
import dev.hoshizora.api.i18n.Term;
import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;
import org.jspecify.annotations.Nullable;

@Schema(description = "Catalogued objects by owner country and by owning organization, from the CelesTrak SATCAT.")
public record ObjectsInOrbit(
        String source,

        @Schema(description = "earth_orbit, beyond_earth or decayed.")
        Term orbitState,

        @Schema(description = "Every object in this state, each counted once.")
        Counts totals,

        @Schema(description = "Objects per owner country. A jointly owned object counts for each member country.")
        List<CountryRow> countries,

        @Schema(description = "Objects owned by an organization code such as ESA, which has no single country.")
        List<OrganizationRow> organizations) {

    @Schema(name = "ObjectCounts")
    public record Counts(long payloads, long rocketBodies, long debris, long unknown, long total) {}

    @Schema(name = "ObjectsByCountry")
    public record CountryRow(
            CountryRef country,
            Counts counts,

            @Schema(description = "Objects of joint owners counted here and for other countries too.")
            long shared) {}

    @Schema(name = "ObjectsByOrganization")
    public record OrganizationRow(
            @Schema(description = "SATCAT owner code.", example = "ESA")
            String ownerCode,

            @Schema(description = "CelesTrak's label for the owner code, in English.")
            String label,

            Lang labelLang,
            @Nullable OrganizationRef organization,
            Counts counts) {}
}
