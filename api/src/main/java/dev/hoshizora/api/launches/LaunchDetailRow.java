package dev.hoshizora.api.launches;

import dev.hoshizora.api.common.LineageEntry;
import dev.hoshizora.api.common.OrganizationRow;
import dev.hoshizora.api.i18n.Bilingual;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import org.jspecify.annotations.Nullable;

record LaunchDetailRow(
        LaunchRow launch,
        @Nullable Instant windowStart,
        @Nullable Instant windowEnd,
        @Nullable String failureReason,
        List<Program> programs,
        List<OrganizationRow> partners,
        List<SpaceObject> objects,
        long objectsTotal,
        List<LineageEntry> lineage) {

    record Program(String slug, Bilingual name) {}

    record SpaceObject(
            int noradId,
            @Nullable String objectId,
            String name,
            String objectType,
            String orbitState,
            @Nullable String ownerCode,
            @Nullable LocalDate decayDate) {}
}
