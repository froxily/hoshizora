package dev.hoshizora.api.spaceweather;

import dev.hoshizora.api.web.ApiValue;

public enum SolarWindResolution implements ApiValue {
    MINUTE("minute"),
    HOUR("hour");

    private final String value;

    SolarWindResolution(String value) {
        this.value = value;
    }

    @Override
    public String value() {
        return value;
    }
}
