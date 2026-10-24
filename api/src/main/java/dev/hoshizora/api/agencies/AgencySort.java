package dev.hoshizora.api.agencies;

import dev.hoshizora.api.web.ApiValue;

public enum AgencySort implements ApiValue {
    MOST_LAUNCHES("-launches"),
    NAME("name");

    private final String value;

    AgencySort(String value) {
        this.value = value;
    }

    @Override
    public String value() {
        return value;
    }
}
