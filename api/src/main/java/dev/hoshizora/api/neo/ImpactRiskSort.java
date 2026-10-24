package dev.hoshizora.api.neo;

import dev.hoshizora.api.web.ApiValue;

public enum ImpactRiskSort implements ApiValue {
    PALERMO("-palermo"),
    PROBABILITY("-probability"),
    TORINO("-torino"),
    DESIGNATION("designation");

    private final String value;

    ImpactRiskSort(String value) {
        this.value = value;
    }

    @Override
    public String value() {
        return value;
    }
}
