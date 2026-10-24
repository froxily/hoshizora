package dev.hoshizora.api.agencies;

import dev.hoshizora.api.common.CountryRef;
import dev.hoshizora.api.common.LineageEntry;
import dev.hoshizora.api.common.OrganizationRef;
import dev.hoshizora.api.common.ProgramRef;
import dev.hoshizora.api.i18n.Lang;
import dev.hoshizora.api.i18n.Term;
import dev.hoshizora.api.launches.LaunchSummary;
import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;
import org.jspecify.annotations.Nullable;

@Schema(description = "An organization profile: identity, launch record, vehicles, catalogued objects and lineage.")
public record AgencyDetail(
        String key,
        String name,
        Lang nameLang,

        @Schema(description = "Where the Japanese name was verified: the official Japanese site or Japanese Wikipedia.")
        @Nullable
        String nameJaSource,

        @Nullable String abbrev,
        @Nullable Term type,
        List<CountryRef> countries,
        List<ProgramRef> programs,
        @Nullable Integer foundingYear,
        @Nullable LaunchStats launches,
        @Nullable Reliability reliability,
        @Nullable OrganizationRef parent,

        @Schema(description = "Organizations whose parent is this one.")
        List<OrganizationRef> members,

        @Schema(description = "The vehicles it flew most, at most five.")
        List<VehicleUsage> topVehicles,

        @Schema(description = "Its latest launch attempts, newest first, at most five.")
        List<LaunchSummary> recentLaunches,

        @Nullable LaunchSummary nextLaunch,

        @Schema(description = "Missions it took part in as a customer or partner.")
        long partnerMissions,

        @Schema(description = "Objects in the CelesTrak SATCAT owned under its own owner codes, such as ESA.") @Nullable
        CataloguedObjects cataloguedObjects,

        List<LineageEntry> lineage) {

    @Schema(name = "AgencyReliability", description = "Recent reliability as a launch provider.")
    public record Reliability(
            @Schema(description = "Completed attempts in the latest window of up to 20.")
            int recentAttempts,

            int recentSuccesses,
            @Nullable Double recentSuccessRate,

            @Schema(description = "Consecutive successes since the latest failure.")
            int currentStreak,

            int longestStreak) {}

    @Schema(name = "AgencyVehicleUsage", description = "A vehicle and how often this organization flew it.")
    public record VehicleUsage(
            int id, String name, Lang nameLang, @Nullable String family, long attempts, long successes) {}

    @Schema(name = "AgencyCataloguedObjects", description = "Catalogued objects by orbit state.")
    public record CataloguedObjects(
            List<String> ownerCodes, long inEarthOrbit, long payloadsInEarthOrbit, long beyondEarth, long decayed) {}
}
