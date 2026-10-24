package dev.hoshizora.api.stats;

import dev.hoshizora.api.web.ApiValue;
import org.jspecify.annotations.Nullable;

public enum LaunchGrouping implements ApiValue {
    ALL("all", null),
    PROGRAM("program", "program"),
    PROVIDER("provider", "provider"),
    VEHICLE_FAMILY("vehicle_family", "vehicle_family"),
    SITE_COUNTRY("site_country", "site_country");

    private final String value;
    private final @Nullable String launchFilter;

    LaunchGrouping(String value, @Nullable String launchFilter) {
        this.value = value;
        this.launchFilter = launchFilter;
    }

    @Override
    public String value() {
        return value;
    }

    @Nullable
    String launchFilter() {
        return launchFilter;
    }
}
