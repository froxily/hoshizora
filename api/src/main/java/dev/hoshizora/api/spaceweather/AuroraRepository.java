package dev.hoshizora.api.spaceweather;

import dev.hoshizora.api.db.Rows;
import dev.hoshizora.api.db.Sql;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class AuroraRepository {

    static final String CACHE = "aurora";

    private static final String LATEST = Sql.load("spaceweather/aurora_latest.sql");
    private static final String CELLS = Sql.load("spaceweather/aurora_cells.sql");
    private static final String HISTORY = Sql.load("spaceweather/aurora_history.sql");

    private final JdbcClient jdbc;

    AuroraRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Cacheable(CACHE)
    public Aurora aurora(int minPercent) {
        var latest = latest(minPercent);
        return new Aurora(latest.orElse(null), latest.map(this::history).orElse(List.of()));
    }

    private Optional<Aurora.Forecast> latest(int minPercent) {
        return jdbc.sql(LATEST)
                .query((rs, n) -> {
                    var observedAt = Objects.requireNonNull(Rows.instant(rs, "observed_at"));
                    return new Aurora.Forecast(
                            observedAt,
                            Objects.requireNonNull(Rows.instant(rs, "forecast_at")),
                            new Aurora.Hemisphere(
                                    rs.getInt("north_max_percent"), Rows.integer(rs, "north_boundary_lat")),
                            new Aurora.Hemisphere(
                                    rs.getInt("south_max_percent"), Rows.integer(rs, "south_boundary_lat")),
                            cells(observedAt, minPercent));
                })
                .optional();
    }

    private List<List<Integer>> cells(Instant observedAt, int minPercent) {
        return jdbc.sql(CELLS)
                .param("observed_at", Timestamp.from(observedAt))
                .param("min_percent", minPercent)
                .query((rs, n) ->
                        List.of(rs.getInt("longitude"), rs.getInt("latitude"), rs.getInt("probability_percent")))
                .list();
    }

    private List<Aurora.Summary> history(Aurora.Forecast latest) {
        return jdbc.sql(HISTORY)
                .param("latest", Timestamp.from(latest.observedAt()))
                .query((rs, n) -> new Aurora.Summary(
                        Objects.requireNonNull(Rows.instant(rs, "observed_at")),
                        rs.getInt("north_max_percent"),
                        rs.getInt("south_max_percent")))
                .list();
    }
}
