package dev.hoshizora.api.spaceweather;

import dev.hoshizora.api.web.ApiValue;

public enum FlareSort implements ApiValue {
    NEWEST("-time"),
    STRONGEST("-flux");

    private final String value;

    FlareSort(String value) {
        this.value = value;
    }

    @Override
    public String value() {
        return value;
    }
}
