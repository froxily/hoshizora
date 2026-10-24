package dev.hoshizora.api.spaceweather;

import dev.hoshizora.api.db.Paged;
import dev.hoshizora.api.db.Sql;
import dev.hoshizora.api.web.Page;
import dev.hoshizora.api.web.PageQuery;
import dev.hoshizora.api.web.Ranges;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import org.jspecify.annotations.Nullable;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class SpaceWeatherRepository {

    static final String NOW_CACHE = "space-weather-now";
    static final String KP_CACHE = "kp";
    static final String FLARES_CACHE = "flares";
    static final String SOLAR_WIND_CACHE = "solar-wind";

    private static final String NOW = Sql.load("spaceweather/now.sql");
    private static final String KP = Sql.load("spaceweather/kp.sql");
    private static final String FLARES = Sql.load("spaceweather/flares.sql");
    private static final String WIND_BY_MINUTE = Sql.load("spaceweather/solar_wind_minute.sql");
    private static final String WIND_BY_HOUR = Sql.load("spaceweather/solar_wind_hour.sql");

    private final JdbcClient jdbc;

    SpaceWeatherRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Cacheable(NOW_CACHE)
    public SpaceWeatherRows.NowRow now(Instant asOf) {
        return jdbc.sql(NOW)
                .param("as_of", Timestamp.from(asOf))
                .query((rs, n) -> SpaceWeatherRows.now(rs))
                .single();
    }

    @Cacheable(KP_CACHE)
    public List<SpaceWeatherRows.KpRow> kp(Ranges.Window window) {
        return jdbc.sql(KP)
                .param("from", Timestamp.from(window.from()))
                .param("to", Timestamp.from(window.to()))
                .query((rs, n) -> SpaceWeatherRows.kp(rs))
                .list();
    }

    @Cacheable(FLARES_CACHE)
    public Page<SpaceWeatherRows.FlareRow> flares(FlareFilter filter, PageQuery query) {
        var statement = jdbc.sql(FLARES)
                .param("from", timestamp(filter.from()))
                .param("to", timestamp(filter.to()))
                .param(
                        "min_flux",
                        filter.minClass() == null ? null : filter.minClass().minimumFluxWm2())
                .param("sort", filter.sort().value());
        return Paged.fetch(statement, query, "id", (rs, n) -> SpaceWeatherRows.flare(rs, ""));
    }

    @Cacheable(SOLAR_WIND_CACHE)
    public List<SolarWind.Point> solarWind(Ranges.Window window, SolarWindResolution resolution) {
        return jdbc.sql(resolution == SolarWindResolution.HOUR ? WIND_BY_HOUR : WIND_BY_MINUTE)
                .param("from", Timestamp.from(window.from()))
                .param("to", Timestamp.from(window.to()))
                .query((rs, n) -> SpaceWeatherRows.wind(rs, "observed_at"))
                .list();
    }

    private static @Nullable Timestamp timestamp(@Nullable Instant instant) {
        return instant == null ? null : Timestamp.from(instant);
    }

    record FlareFilter(
            @Nullable Instant from,
            @Nullable Instant to,
            @Nullable FlareClass minClass,
            FlareSort sort) {}
}
