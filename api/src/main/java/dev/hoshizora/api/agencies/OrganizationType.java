package dev.hoshizora.api.agencies;

import dev.hoshizora.api.web.ApiValue;

public enum OrganizationType implements ApiValue {
    AGENCY("agency"),
    COMPANY("company"),
    MILITARY("military"),
    ACADEMIC("academic"),
    INTERNATIONAL("international");

    private final String value;

    OrganizationType(String value) {
        this.value = value;
    }

    @Override
    public String value() {
        return value;
    }
}
