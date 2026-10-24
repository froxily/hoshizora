package dev.hoshizora.api.stats;

import dev.hoshizora.api.db.Sql;
import java.util.List;
import org.jspecify.annotations.Nullable;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class ExoplanetStatsRepository {

    static final String DISCOVERIES_CACHE = "exoplanet-discoveries";
    static final String SIZE_ORBIT_CACHE = "exoplanet-size-orbit";
    static final double PERIOD_STEP_DEX = 0.25;
    static final double RADIUS_STEP_DEX = 0.125;

    private static final String DISCOVERIES = Sql.load("stats/exoplanet_discoveries.sql");
    private static final String SIZE_ORBIT = Sql.load("stats/exoplanet_size_orbit.sql");

    private final JdbcClient jdbc;

    ExoplanetStatsRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    record DiscoveryRow(int year, String method, long planets, long fromSpace) {}

    record SizeOrbitRow(int periodBin, int radiusBin, long planets) {}

    @Cacheable(DISCOVERIES_CACHE)
    public List<DiscoveryRow> discoveries(@Nullable Integer fromYear, @Nullable Integer toYear) {
        return jdbc.sql(DISCOVERIES)
                .param("from_year", fromYear)
                .param("to_year", toYear)
                .query((rs, n) -> new DiscoveryRow(
                        rs.getInt("year"), rs.getString("method"), rs.getLong("planets"), rs.getLong("from_space")))
                .list();
    }

    @Cacheable(SIZE_ORBIT_CACHE)
    public List<SizeOrbitRow> sizeOrbit() {
        return jdbc.sql(SIZE_ORBIT)
                .query((rs, n) ->
                        new SizeOrbitRow(rs.getInt("period_bin"), rs.getInt("radius_bin"), rs.getLong("planets")))
                .list();
    }
}
