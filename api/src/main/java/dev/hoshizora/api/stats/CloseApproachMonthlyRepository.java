package dev.hoshizora.api.stats;

import dev.hoshizora.api.db.Rows;
import dev.hoshizora.api.db.Sql;
import dev.hoshizora.api.web.Ranges;
import java.time.LocalDate;
import java.util.List;
import java.util.Objects;
import org.jspecify.annotations.Nullable;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class CloseApproachMonthlyRepository {

    private static final String MONTHLY = Sql.load("stats/close_approach_monthly.sql");

    private final JdbcClient jdbc;

    CloseApproachMonthlyRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    record MonthRow(
            LocalDate month,
            long approaches,
            long withinLunarDistance,
            double closestDistLd,
            String closestDesignation,
            @Nullable Double minAbsoluteMagnitude,
            @Nullable String largestDesignation) {}

    @Cacheable(NeoStatsController.CACHE)
    public List<MonthRow> monthly(Ranges.Dates dates) {
        return jdbc.sql(MONTHLY)
                .param("from", dates.from())
                .param("to", dates.to())
                .query((rs, n) -> new MonthRow(
                        Objects.requireNonNull(Rows.date(rs, "month")),
                        rs.getLong("approaches"),
                        rs.getLong("within_1_ld"),
                        rs.getDouble("closest_dist_ld"),
                        rs.getString("closest_designation"),
                        Rows.decimal(rs, "min_h_mag"),
                        rs.getString("largest_designation")))
                .list();
    }
}
