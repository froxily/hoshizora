package dev.hoshizora.api.neo;

import org.jspecify.annotations.Nullable;

record ImpactRiskQuery(
        @Nullable String designation,
        @Nullable Double minPalermo,
        @Nullable Integer minTorino,
        boolean includeRemoved,
        ImpactRiskSort sort) {

    static ImpactRiskQuery of(String designation) {
        return new ImpactRiskQuery(designation, null, null, true, ImpactRiskSort.DESIGNATION);
    }
}
