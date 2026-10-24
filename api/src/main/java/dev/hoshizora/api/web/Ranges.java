package dev.hoshizora.api.web;

import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import org.jspecify.annotations.Nullable;

public final class Ranges {

    private Ranges() {}

    public record Window(Instant from, Instant to) {}

    public record Dates(LocalDate from, LocalDate to) {}

    public static Window window(
            @Nullable Instant from, @Nullable Instant to, Instant now, Duration fallback, Duration longest) {
        var end = to == null ? now.truncatedTo(ChronoUnit.HOURS).plus(Duration.ofHours(1)) : to;
        var start = from == null ? end.minus(fallback) : from;
        if (!start.isBefore(end)) {
            throw new InvalidParameterException("from", "validation.range_order");
        }
        if (Duration.between(start, end).compareTo(longest) > 0) {
            throw new InvalidParameterException("from", "validation.range_length", longest.toDays());
        }
        return new Window(start, end);
    }

    public static Dates dates(@Nullable LocalDate from, @Nullable LocalDate to, Dates fallback, long longestDays) {
        var start = from == null ? fallback.from() : from;
        var end = to == null ? fallback.to() : to;
        if (!start.isBefore(end)) {
            throw new InvalidParameterException("from", "validation.range_order");
        }
        if (ChronoUnit.DAYS.between(start, end) > longestDays) {
            throw new InvalidParameterException("from", "validation.range_length", longestDays);
        }
        return new Dates(start, end);
    }

    public static void ordered(@Nullable LocalDate from, @Nullable LocalDate to) {
        if (from != null && to != null && !from.isBefore(to)) {
            throw new InvalidParameterException("from", "validation.range_order");
        }
    }

    public static void ordered(@Nullable Instant from, @Nullable Instant to) {
        if (from != null && to != null && !from.isBefore(to)) {
            throw new InvalidParameterException("from", "validation.range_order");
        }
    }
}
