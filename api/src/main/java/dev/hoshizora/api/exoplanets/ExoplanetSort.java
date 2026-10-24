package dev.hoshizora.api.exoplanets;

import dev.hoshizora.api.web.ApiValue;

public enum ExoplanetSort implements ApiValue {
    DISTANCE("distance"),
    NEWEST("-discovery_year"),
    RADIUS("radius"),
    NAME("name");

    private final String value;

    ExoplanetSort(String value) {
        this.value = value;
    }

    @Override
    public String value() {
        return value;
    }
}
