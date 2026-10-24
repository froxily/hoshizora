package dev.hoshizora.api.exoplanets;

import dev.hoshizora.api.common.Lineage;
import dev.hoshizora.api.common.LineageEntry;
import dev.hoshizora.api.db.Paged;
import dev.hoshizora.api.db.Rows;
import dev.hoshizora.api.db.Sql;
import dev.hoshizora.api.web.Page;
import dev.hoshizora.api.web.PageQuery;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.Optional;
import org.jspecify.annotations.Nullable;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class ExoplanetRepository {

    static final String LIST_CACHE = "exoplanets";
    static final String DETAIL_CACHE = "exoplanet";

    private static final String LIST = Sql.load("exoplanets/list.sql");

    private final JdbcClient jdbc;
    private final Lineage lineage;

    ExoplanetRepository(JdbcClient jdbc, Lineage lineage) {
        this.jdbc = jdbc;
        this.lineage = lineage;
    }

    record Query(
            @Nullable String name,
            @Nullable String method,
            @Nullable Integer fromYear,
            @Nullable Integer toYear,
            @Nullable Double maxDistanceLy,
            boolean includeControversial,
            ExoplanetSort sort) {}

    record Row(
            String name,
            String hostName,
            @Nullable Integer starCount,
            @Nullable Integer planetCount,
            String discoveryMethod,
            @Nullable Integer discoveryYear,
            @Nullable String discoveryFacility,
            @Nullable String discoveryLocale,
            @Nullable Double orbitalPeriodDays,
            @Nullable Double semiMajorAxisAu,
            @Nullable Double radiusEarth,
            @Nullable Double massEarth,
            @Nullable Double eccentricity,
            @Nullable Double equilibriumTempK,
            @Nullable Double insolationEarth,
            @Nullable Double starTempK,
            @Nullable Double starRadiusSun,
            @Nullable Double starMassSun,
            @Nullable Double distancePc,
            boolean controversial) {}

    record Detail(Row planet, List<LineageEntry> lineage) {}

    @Cacheable(LIST_CACHE)
    public Page<Row> list(Query query, PageQuery paging) {
        return Paged.fetch(statement(query), paging, "name", (rs, n) -> row(rs));
    }

    @Cacheable(DETAIL_CACHE)
    public Optional<Detail> detail(String name) {
        var query = new Query(name, null, null, null, null, true, ExoplanetSort.NAME);
        return Paged.fetch(statement(query), PageQuery.first(1), "name", (rs, n) -> row(rs)).items().stream()
                .findFirst()
                .map(row -> new Detail(row, lineage.of("core.exoplanet", name)));
    }

    private JdbcClient.StatementSpec statement(Query query) {
        return jdbc.sql(LIST)
                .param("name", query.name())
                .param("method", query.method())
                .param("from_year", query.fromYear())
                .param("to_year", query.toYear())
                .param("max_distance_ly", query.maxDistanceLy())
                .param("include_controversial", query.includeControversial())
                .param("sort", query.sort().value());
    }

    private static Row row(ResultSet rs) throws SQLException {
        return new Row(
                rs.getString("name"),
                rs.getString("host_name"),
                Rows.integer(rs, "star_count"),
                Rows.integer(rs, "planet_count"),
                rs.getString("discovery_method"),
                Rows.integer(rs, "discovery_year"),
                rs.getString("discovery_facility"),
                rs.getString("discovery_locale"),
                Rows.decimal(rs, "orbital_period_days"),
                Rows.decimal(rs, "semi_major_axis_au"),
                Rows.decimal(rs, "radius_earth"),
                Rows.decimal(rs, "mass_earth"),
                Rows.decimal(rs, "eccentricity"),
                Rows.decimal(rs, "equilibrium_temp_k"),
                Rows.decimal(rs, "insolation_earth"),
                Rows.decimal(rs, "star_temp_k"),
                Rows.decimal(rs, "star_radius_sun"),
                Rows.decimal(rs, "star_mass_sun"),
                Rows.decimal(rs, "distance_pc"),
                rs.getBoolean("controversial"));
    }
}
