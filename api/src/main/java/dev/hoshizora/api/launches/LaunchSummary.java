package dev.hoshizora.api.launches;

import dev.hoshizora.api.common.CountryRef;
import dev.hoshizora.api.common.OrganizationRef;
import dev.hoshizora.api.i18n.Lang;
import dev.hoshizora.api.i18n.Term;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;
import java.util.UUID;
import org.jspecify.annotations.Nullable;

@Schema(description = "A launch with its provider, vehicle, pad and mission.")
public record LaunchSummary(
        @Schema(description = "Launch Library 2 launch id.") UUID id,

        @Schema(description = "Launch Library 2 name, usually vehicle | mission.")
        String name,

        Lang nameLang,

        @Schema(description = "No earlier than: the launch time, or the planned one for upcoming launches.") @Nullable
        Instant net,

        @Schema(description = "How precise net is, from to the second to a decade.") @Nullable
        Term netPrecision,

        @Schema(description = "success, failure, partial_failure, in_flight, upcoming or unknown.")
        Term status,

        @Schema(description = "COSPAR international designator of the launch (YYYY-NNN).", example = "2017-062")
        @Nullable
        String launchDesignator,

        @Schema(description = "The launch service provider, which is not necessarily the customer or agency.") @Nullable
        OrganizationRef provider,

        @Nullable Vehicle vehicle,
        @Nullable Pad pad,
        @Nullable Mission mission) {

    @Schema(name = "LaunchVehicle", description = "The launcher configuration, e.g. H-IIA 202.")
    public record Vehicle(
            int id,
            String name,
            Lang nameLang,
            @Nullable String family,
            @Nullable String variant) {}

    @Schema(name = "LaunchPad", description = "The pad, its site and the country it is in.")
    public record Pad(
            int id,
            String name,
            Lang nameLang,

            @Schema(description = "The launch site, e.g. Tanegashima Space Center.") @Nullable
            String location,

            @Nullable CountryRef country,
            @Nullable Double latitude,
            @Nullable Double longitude) {}

    @Schema(name = "LaunchMission", description = "The primary mission, its type and target orbit.")
    public record Mission(
            int id,
            String name,
            Lang nameLang,
            @Nullable Term type,
            @Nullable Term orbit,

            @Schema(description = "Launch Library 2 description, only in the detail view and only in English.")
            @Nullable
            String description,

            @Nullable Lang descriptionLang) {}
}
