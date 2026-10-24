package dev.hoshizora.api.launches;

import dev.hoshizora.api.web.ApiValue;

public enum LaunchSort implements ApiValue {
    NET_ASCENDING("net"),
    NET_DESCENDING("-net");

    private final String value;

    LaunchSort(String value) {
        this.value = value;
    }

    @Override
    public String value() {
        return value;
    }
}
