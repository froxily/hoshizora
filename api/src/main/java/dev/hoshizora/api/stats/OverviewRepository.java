package dev.hoshizora.api.stats;

import dev.hoshizora.api.db.Rows;
import dev.hoshizora.api.db.Sql;
import dev.hoshizora.api.launches.LaunchRow;
import dev.hoshizora.api.launches.LaunchRows;
import dev.hoshizora.api.neo.CloseApproachRow;
import java.sql.Timestamp;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import org.jspecify.annotations.Nullable;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class OverviewRepository {

    static final String CACHE = "overview";

    private static final String OVERVIEW = Sql.load("stats/overview.sql");
    private static final String NEXT_LAUNCH = Sql.load("stats/next_launch.sql");
    private static final String CLOSEST_APPROACH = Sql.load("stats/closest_approach_week.sql");

    private final JdbcClient jdbc;

    OverviewRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    record Snapshot(
            long launchesThisYear,
            long launchesSamePeriodLastYear,
            @Nullable Instant kpObservedAt,
            double kp,
            int gScale,
            long objectsInEarthOrbit,
            long payloadsInEarthOrbit,
            @Nullable LaunchRow nextLaunch,
            @Nullable CloseApproachRow closestApproach) {}

    @Cacheable(CACHE)
    public Snapshot snapshot(Instant asOf) {
        var date = asOf.atZone(ZoneOffset.UTC);
        var yearStart = date.withDayOfYear(1).toLocalDate().atStartOfDay(ZoneOffset.UTC);
        var lastYearStart = yearStart.minusYears(1);
        var lastYearAsOf = date.minusYears(1);
        var nextLaunch = jdbc.sql(NEXT_LAUNCH)
                .param("as_of", Timestamp.from(asOf))
                .query((rs, n) -> LaunchRows.summary(rs))
                .optional()
                .orElse(null);
        var closest = jdbc.sql(CLOSEST_APPROACH)
                .param("as_of", Timestamp.from(asOf))
                .param("until", Timestamp.from(asOf.plus(Duration.ofDays(7))))
                .query((rs, n) -> CloseApproachRow.of(rs))
                .optional()
                .orElse(null);
        return jdbc.sql(OVERVIEW)
                .param("as_of", Timestamp.from(asOf))
                .param("year_start", Timestamp.from(yearStart.toInstant()))
                .param("last_year_start", Timestamp.from(lastYearStart.toInstant()))
                .param("last_year_as_of", Timestamp.from(lastYearAsOf.toInstant()))
                .query((rs, n) -> new Snapshot(
                        rs.getLong("launches_this_year"),
                        rs.getLong("launches_same_period_last_year"),
                        Rows.instant(rs, "kp_observed_at"),
                        rs.getDouble("kp"),
                        rs.getInt("g_scale"),
                        rs.getLong("objects_in_earth_orbit"),
                        rs.getLong("payloads_in_earth_orbit"),
                        nextLaunch,
                        closest))
                .single();
    }
}
