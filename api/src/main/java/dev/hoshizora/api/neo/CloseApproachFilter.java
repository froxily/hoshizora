package dev.hoshizora.api.neo;

import java.time.LocalDate;
import org.jspecify.annotations.Nullable;

record CloseApproachFilter(
        @Nullable LocalDate from,
        @Nullable LocalDate to,
        @Nullable Double maxDistLd,
        @Nullable Double maxH,
        @Nullable String designation,
        @Nullable Boolean sentry,
        CloseApproachSort sort) {

    static CloseApproachFilter of(String designation) {
        return new CloseApproachFilter(null, null, null, null, designation, null, CloseApproachSort.DATE);
    }
}
