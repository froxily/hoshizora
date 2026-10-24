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
class SpaceWeatherStatsRepository {

    static final String FLARES_CACHE = "flares-monthly";
    static final String KP_CACHE = "kp-daily";

    private static final String FLARES = Sql.load("stats/flares_monthly.sql");
    private static final String KP = Sql.load("stats/kp_daily.sql");

    private final JdbcClient jdbc;

    SpaceWeatherStatsRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    record FlareMonth(
            LocalDate month,
            long total,
            FlaresMonthly.ClassCounts byClass,
            @Nullable Double maxPeakFluxWm2,
            @Nullable String strongestClass) {}

    record KpDay(LocalDate day, double kpMax, double kpMean, int intervals, int gScale) {}

    @Cacheable(FLARES_CACHE)
    public List<FlareMonth> flares(Ranges.Dates dates) {
        return jdbc.sql(FLARES)
                .param("from", dates.from())
                .param("to", dates.to())
                .query((rs, n) -> new FlareMonth(
                        Objects.requireNonNull(Rows.date(rs, "month")),
                        rs.getLong("total"),
                        new FlaresMonthly.ClassCounts(
                                rs.getLong("a"), rs.getLong("b"), rs.getLong("c"), rs.getLong("m"), rs.getLong("x")),
                        Rows.decimal(rs, "max_peak_flux_wm2"),
                        rs.getString("strongest_class")))
                .list();
    }

    @Cacheable(KP_CACHE)
    public List<KpDay> kp(Ranges.Dates dates) {
        return jdbc.sql(KP)
                .param("from", dates.from())
                .param("to", dates.to())
                .query((rs, n) -> new KpDay(
                        Objects.requireNonNull(Rows.date(rs, "day")),
                        rs.getDouble("kp_max"),
                        rs.getDouble("kp_mean"),
                        rs.getInt("intervals"),
                        rs.getInt("g_scale")))
                .list();
    }
}
