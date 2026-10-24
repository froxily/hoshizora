package dev.hoshizora.api.launches;

import dev.hoshizora.api.common.LineageEntry;
import dev.hoshizora.api.common.OrganizationRef;
import dev.hoshizora.api.common.ProgramRef;
import dev.hoshizora.api.i18n.Lang;
import dev.hoshizora.api.i18n.Term;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;
import org.jspecify.annotations.Nullable;

@Schema(description = "A launch with its window, programs, partners, catalogued objects and source lineage.")
public record LaunchDetail(
        UUID id,
        String name,
        Lang nameLang,
        @Nullable Instant net,
        @Nullable Term netPrecision,
        Term status,
        @Nullable String launchDesignator,
        @Nullable OrganizationRef provider,
        LaunchSummary.@Nullable Vehicle vehicle,
        LaunchSummary.@Nullable Pad pad,
        LaunchSummary.@Nullable Mission mission,
        @Nullable Instant windowStart,
        @Nullable Instant windowEnd,

        @Schema(description = "Why the launch failed, as Launch Library 2 states it, in English.") @Nullable
        String failureReason,

        @Nullable Lang failureReasonLang,

        @Schema(description = "National programs the provider belongs to.")
        List<ProgramRef> programs,

        @Schema(description = "Customers and partner agencies of the mission.")
        List<OrganizationRef> partners,

        @Schema(description = "Catalogued objects from this launch (CelesTrak SATCAT), payloads first, at most 100.")
        List<LaunchObject> objects,

        @Schema(description = "How many catalogued objects this launch produced in total.")
        long objectsTotal,

        @Schema(description = "The source responses behind this record, newest first.")
        List<LineageEntry> lineage) {

    @Schema(description = "A catalogued object from a launch.")
    public record LaunchObject(
            int noradId,

            @Schema(description = "COSPAR id of the object.", example = "2017-062A") @Nullable
            String objectId,

            @Schema(description = "SATCAT name, in English.")
            String name,

            @Schema(description = "payload, rocket_body, debris or unknown.")
            Term objectType,

            @Schema(description = "earth_orbit, beyond_earth or decayed.")
            Term orbitState,

            @Schema(description = "SATCAT owner code, a country or organization.") @Nullable
            String ownerCode,

            @Nullable LocalDate decayDate) {}
}
