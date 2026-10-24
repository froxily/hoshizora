package dev.hoshizora.api.launches;

import dev.hoshizora.api.common.OrganizationRow;
import dev.hoshizora.api.i18n.Bilingual;
import java.time.Instant;
import java.util.UUID;
import org.jspecify.annotations.Nullable;

public record LaunchRow(
        UUID id,
        String name,
        @Nullable Instant net,
        @Nullable String netPrecision,
        String outcome,
        @Nullable String launchDesignator,
        @Nullable Long providerOrganizationId,
        @Nullable OrganizationRow provider,
        @Nullable Vehicle vehicle,
        @Nullable Pad pad,
        @Nullable Mission mission) {

    public record Vehicle(
            int id,
            Bilingual name,
            @Nullable String family,
            @Nullable String variant) {}

    public record Pad(
            int id,
            String name,
            @Nullable String location,
            @Nullable String countryCode,
            @Nullable String countryEn,
            @Nullable String countryJa,
            @Nullable Double latitude,
            @Nullable Double longitude) {}

    public record Mission(
            int id,
            Bilingual name,
            @Nullable String type,
            @Nullable String orbit,
            @Nullable String orbitName,
            @Nullable String description) {}
}
