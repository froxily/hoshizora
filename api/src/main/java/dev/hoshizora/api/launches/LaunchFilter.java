package dev.hoshizora.api.launches;

import java.time.Instant;
import org.jspecify.annotations.Nullable;

record LaunchFilter(
        @Nullable Instant from,
        @Nullable Instant to,
        @Nullable LaunchOutcome status,
        @Nullable String provider,
        @Nullable String program,
        @Nullable String vehicleFamily,
        @Nullable String siteCountry,
        @Nullable Integer pad,
        LaunchSort sort) {}
