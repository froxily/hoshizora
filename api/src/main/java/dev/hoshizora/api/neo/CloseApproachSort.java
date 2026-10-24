package dev.hoshizora.api.neo;

import dev.hoshizora.api.web.ApiValue;

public enum CloseApproachSort implements ApiValue {
    DATE("date"),
    DATE_DESCENDING("-date"),
    DISTANCE("distance");

    private final String value;

    CloseApproachSort(String value) {
        this.value = value;
    }

    @Override
    public String value() {
        return value;
    }
}
