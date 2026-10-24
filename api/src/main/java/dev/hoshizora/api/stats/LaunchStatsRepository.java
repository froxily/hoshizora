package dev.hoshizora.api.stats;

import dev.hoshizora.api.db.Rows;
import dev.hoshizora.api.db.Sql;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.function.BiFunction;
import java.util.function.Function;
import org.jspecify.annotations.Nullable;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class LaunchStatsRepository {

    static final String CADENCE_CACHE = "launch-cadence";
    static final String SUCCESS_CACHE = "launch-success";
    static final String PADS_CACHE = "launch-pads";
    static final String REUSABILITY_CACHE = "launch-reusability";
    static final String BOOSTERS_CACHE = "launch-boosters";

    private static final String CADENCE = Sql.load("stats/launch_cadence.sql");
    private static final String SUCCESS = Sql.load("stats/launch_success.sql");
    private static final String PADS = Sql.load("stats/launch_pads.sql");
    private static final String REUSABILITY = Sql.load("stats/launch_reusability.sql");
    private static final String BOOSTERS = Sql.load("stats/launch_boosters.sql");

    private final JdbcClient jdbc;

    LaunchStatsRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    record GroupQuery(
            LaunchGrouping groupBy,
            @Nullable String key,
            @Nullable Integer fromYear,
            @Nullable Integer toYear,
            int limit) {}

    record Named(
            String key, @Nullable String nameEn, @Nullable String nameJa) {}

    record CadenceSeries(Named group, long totalAttempts, List<CadenceYear> years) {}

    record CadenceYear(int year, long attempts, long successes, long failures, long partialFailures, long scheduled) {}

    record SuccessGroup(
            Named group,
            long attempts,
            long successes,
            int recentAttempts,
            int recentSuccesses,
            int currentStreak,
            int longestStreak,
            List<SuccessYear> years) {}

    record SuccessYear(int year, long attemptsToDate, long successesToDate, int recentAttempts, int recentSuccesses) {}

    record PadRow(
            int padId,
            String name,
            @Nullable String location,
            @Nullable String countryCode,
            @Nullable String countryEn,
            @Nullable String countryJa,
            @Nullable Double latitude,
            @Nullable Double longitude,
            long attempts,
            long successes,
            long failures,
            long scheduled,
            @Nullable Instant firstLaunchAt,
            @Nullable Instant lastLaunchAt,
            @Nullable Integer busiestYear,
            @Nullable Long busiestYearAttempts) {}

    record ReusabilitySeries(Named group, long totalStageFlights, List<ReusabilityYear> years) {}

    record ReusabilityYear(
            int year,
            long launches,
            long launchesReflown,
            long stageFlights,
            long stageReflights,
            long landingAttempts,
            long landings) {}

    record BoosterQuery(@Nullable String provider, @Nullable Boolean active, int limit) {}

    record BoosterRow(
            int launcherId,
            String serialNumber,
            @Nullable String status,
            @Nullable Integer vehicleId,
            @Nullable String vehicleName,
            @Nullable String vehicleNameJa,
            @Nullable String vehicleFamily,
            long flights,
            @Nullable Long attemptedLandings,
            @Nullable Long successfulLandings,
            @Nullable Instant firstLaunchAt,
            @Nullable Instant lastLaunchAt,
            @Nullable Double fastestTurnaroundDays,
            long rank) {}

    @Cacheable(CADENCE_CACHE)
    public List<CadenceSeries> cadence(GroupQuery query) {
        var rows = jdbc.sql(CADENCE)
                .param("group_by", query.groupBy().value())
                .param("key", query.key())
                .param("from_year", query.fromYear())
                .param("to_year", query.toYear())
                .param("limit", query.limit())
                .query((rs, n) -> new CadenceRow(
                        named(rs),
                        rs.getLong("total_attempts"),
                        new CadenceYear(
                                rs.getInt("year"),
                                rs.getLong("attempts"),
                                rs.getLong("successes"),
                                rs.getLong("failures"),
                                rs.getLong("partial_failures"),
                                rs.getLong("scheduled"))))
                .list();
        return grouped(
                rows,
                CadenceRow::group,
                CadenceRow::year,
                (first, years) -> new CadenceSeries(first.group(), first.totalAttempts(), years));
    }

    @Cacheable(SUCCESS_CACHE)
    public List<SuccessGroup> success(GroupQuery query) {
        var rows = jdbc.sql(SUCCESS)
                .param("group_by", query.groupBy().value())
                .param("key", query.key())
                .param("limit", query.limit())
                .query((rs, n) -> new SuccessRow(
                        named(rs),
                        rs.getLong("attempts"),
                        rs.getLong("successes"),
                        rs.getInt("recent_attempts"),
                        rs.getInt("recent_successes"),
                        rs.getInt("current_streak"),
                        rs.getInt("longest_streak"),
                        new SuccessYear(
                                rs.getInt("year"),
                                rs.getLong("year_attempts_to_date"),
                                rs.getLong("year_successes_to_date"),
                                rs.getInt("year_recent_attempts"),
                                rs.getInt("year_recent_successes"))))
                .list();
        return grouped(
                rows,
                SuccessRow::group,
                SuccessRow::year,
                (first, years) -> new SuccessGroup(
                        first.group(),
                        first.attempts(),
                        first.successes(),
                        first.recentAttempts(),
                        first.recentSuccesses(),
                        first.currentStreak(),
                        first.longestStreak(),
                        years));
    }

    @Cacheable(PADS_CACHE)
    public List<PadRow> pads(@Nullable String country, int limit) {
        return jdbc.sql(PADS)
                .param("country", country)
                .param("limit", limit)
                .query((rs, n) -> new PadRow(
                        rs.getInt("pad_id"),
                        rs.getString("pad_name"),
                        rs.getString("pad_location"),
                        rs.getString("country_code"),
                        rs.getString("country_en"),
                        rs.getString("country_ja"),
                        Rows.decimal(rs, "latitude"),
                        Rows.decimal(rs, "longitude"),
                        rs.getLong("attempts"),
                        rs.getLong("successes"),
                        rs.getLong("failures"),
                        rs.getLong("scheduled"),
                        Rows.instant(rs, "first_launch_at"),
                        Rows.instant(rs, "last_launch_at"),
                        Rows.integer(rs, "busiest_year"),
                        Rows.whole(rs, "busiest_year_attempts")))
                .list();
    }

    @Cacheable(REUSABILITY_CACHE)
    public List<ReusabilitySeries> reusability(GroupQuery query) {
        var rows = jdbc.sql(REUSABILITY)
                .param("group_by", query.groupBy().value())
                .param("key", query.key())
                .param("from_year", query.fromYear())
                .param("to_year", query.toYear())
                .param("limit", query.limit())
                .query((rs, n) -> new ReusabilityRow(
                        named(rs),
                        rs.getLong("total_stage_flights"),
                        new ReusabilityYear(
                                rs.getInt("year"),
                                rs.getLong("launches"),
                                rs.getLong("launches_reflown"),
                                rs.getLong("stage_flights"),
                                rs.getLong("stage_reflights"),
                                rs.getLong("landing_attempts"),
                                rs.getLong("landings"))))
                .list();
        return grouped(
                rows,
                ReusabilityRow::group,
                ReusabilityRow::year,
                (first, years) -> new ReusabilitySeries(first.group(), first.totalStageFlights(), years));
    }

    @Cacheable(BOOSTERS_CACHE)
    public List<BoosterRow> boosters(BoosterQuery query) {
        return jdbc.sql(BOOSTERS)
                .param("provider", query.provider())
                .param("active", query.active())
                .param("limit", query.limit())
                .query((rs, n) -> new BoosterRow(
                        rs.getInt("launcher_id"),
                        rs.getString("serial_number"),
                        rs.getString("status"),
                        Rows.integer(rs, "vehicle_ll2_id"),
                        rs.getString("vehicle_name"),
                        rs.getString("vehicle_name_ja"),
                        rs.getString("vehicle_family"),
                        rs.getLong("flights"),
                        Rows.whole(rs, "attempted_landings"),
                        Rows.whole(rs, "successful_landings"),
                        Rows.instant(rs, "first_launch_at"),
                        Rows.instant(rs, "last_launch_at"),
                        Rows.decimal(rs, "fastest_turnaround_days"),
                        rs.getLong("flights_rank")))
                .list();
    }

    private static Named named(ResultSet rs) throws SQLException {
        return new Named(rs.getString("group_key"), rs.getString("name_en"), rs.getString("name_ja"));
    }

    private static <R, Y, G> List<G> grouped(
            List<R> rows, Function<R, Named> group, Function<R, Y> year, BiFunction<R, List<Y>, G> build) {
        var byKey = new LinkedHashMap<String, List<R>>();
        rows.forEach(row -> byKey.computeIfAbsent(group.apply(row).key(), key -> new ArrayList<>())
                .add(row));
        return byKey.values().stream()
                .map(members -> build.apply(
                        members.getFirst(), members.stream().map(year).toList()))
                .toList();
    }

    private record ReusabilityRow(Named group, long totalStageFlights, ReusabilityYear year) {}

    private record CadenceRow(Named group, long totalAttempts, CadenceYear year) {}

    private record SuccessRow(
            Named group,
            long attempts,
            long successes,
            int recentAttempts,
            int recentSuccesses,
            int currentStreak,
            int longestStreak,
            SuccessYear year) {}
}
