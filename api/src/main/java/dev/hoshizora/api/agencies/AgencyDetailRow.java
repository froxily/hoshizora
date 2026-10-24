package dev.hoshizora.api.agencies;

import dev.hoshizora.api.common.LineageEntry;
import dev.hoshizora.api.common.OrganizationRow;
import dev.hoshizora.api.i18n.Bilingual;
import dev.hoshizora.api.launches.LaunchRow;
import java.util.List;
import org.jspecify.annotations.Nullable;

record AgencyDetailRow(
        AgencyRow profile,
        @Nullable OrganizationRow parent,
        List<OrganizationRow> members,
        List<VehicleUsage> vehicles,
        List<LaunchRow> recentLaunches,
        @Nullable LaunchRow nextLaunch,
        @Nullable Reliability reliability,
        @Nullable CataloguedObjects objects,
        long partnerMissions,
        List<LineageEntry> lineage) {

    record VehicleUsage(
            int vehicleId, Bilingual name, @Nullable String family, long attempts, long successes) {}

    record Reliability(int recentAttempts, int recentSuccesses, int currentStreak, int longestStreak) {}

    record CataloguedObjects(
            List<String> ownerCodes, long inEarthOrbit, long payloadsInEarthOrbit, long beyondEarth, long decayed) {}
}
