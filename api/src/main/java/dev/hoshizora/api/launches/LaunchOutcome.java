package dev.hoshizora.api.launches;

import dev.hoshizora.api.web.ApiValue;

public enum LaunchOutcome implements ApiValue {
    SUCCESS("success"),
    FAILURE("failure"),
    PARTIAL_FAILURE("partial_failure"),
    IN_FLIGHT("in_flight"),
    UPCOMING("upcoming"),
    UNKNOWN("unknown");

    private final String value;

    LaunchOutcome(String value) {
        this.value = value;
    }

    @Override
    public String value() {
        return value;
    }
}
