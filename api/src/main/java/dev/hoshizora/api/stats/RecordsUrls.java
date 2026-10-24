package dev.hoshizora.api.stats;

import java.time.LocalDate;
import java.time.ZoneOffset;
import org.jspecify.annotations.Nullable;
import org.springframework.web.util.UriComponentsBuilder;

final class RecordsUrls {

    private RecordsUrls() {}

    static String launches(LaunchGrouping grouping, String key, @Nullable Integer year) {
        var builder = UriComponentsBuilder.fromPath("/api/v1/launches");
        if (grouping.launchFilter() != null) {
            builder.queryParam(grouping.launchFilter(), key);
        }
        if (year != null) {
            builder.queryParam("from", startOfYear(year)).queryParam("to", startOfYear(year + 1));
        }
        return builder.encode().build().toUriString();
    }

    static String launchesFromPad(int padId) {
        return UriComponentsBuilder.fromPath("/api/v1/launches")
                .queryParam("pad", padId)
                .build()
                .toUriString();
    }

    private static String startOfYear(int year) {
        return LocalDate.of(year, 1, 1).atStartOfDay().toInstant(ZoneOffset.UTC).toString();
    }
}
