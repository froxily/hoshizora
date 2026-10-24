package dev.hoshizora.api.agencies;

import org.jspecify.annotations.Nullable;

record AgencyFilter(
        @Nullable OrganizationType type,
        @Nullable String country,
        @Nullable String program,
        @Nullable Boolean hasLaunches,
        @Nullable String query,
        AgencySort sort) {}
