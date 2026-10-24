package dev.hoshizora.api.stats;

import dev.hoshizora.api.web.ApiValue;

public enum OrbitState implements ApiValue {
    EARTH_ORBIT("earth_orbit"),
    BEYOND_EARTH("beyond_earth"),
    DECAYED("decayed");

    private final String value;

    OrbitState(String value) {
        this.value = value;
    }

    @Override
    public String value() {
        return value;
    }
}
