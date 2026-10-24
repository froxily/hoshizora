package dev.hoshizora.api.stats;

import dev.hoshizora.api.common.OrganizationRow;
import dev.hoshizora.api.db.Sql;
import dev.hoshizora.api.i18n.Bilingual;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import org.jspecify.annotations.Nullable;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class OrbitStatsRepository {

    static final String CACHE = "objects-in-orbit";

    private static final String COUNTRIES = Sql.load("stats/orbit_countries.sql");
    private static final String ORGANIZATIONS = Sql.load("stats/orbit_organizations.sql");
    private static final String TOTALS = Sql.load("stats/orbit_totals.sql");

    private final JdbcClient jdbc;

    OrbitStatsRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    record Country(String code, Bilingual name, ObjectsInOrbit.Counts counts, long shared) {}

    record Owner(
            String ownerCode, String label, @Nullable OrganizationRow organization, ObjectsInOrbit.Counts counts) {}

    record Snapshot(ObjectsInOrbit.Counts totals, List<Country> countries, List<Owner> owners) {}

    @Cacheable(CACHE)
    public Snapshot snapshot(OrbitState state, int limit) {
        var totals = jdbc.sql(TOTALS)
                .param("orbit_state", state.value())
                .query((rs, n) -> counts(rs))
                .single();
        var countries = jdbc.sql(COUNTRIES)
                .param("orbit_state", state.value())
                .param("limit", limit)
                .query((rs, n) -> new Country(
                        rs.getString("country_code"),
                        new Bilingual(rs.getString("name_en"), rs.getString("name_ja")),
                        counts(rs),
                        rs.getLong("shared")))
                .list();
        var owners = jdbc.sql(ORGANIZATIONS)
                .param("orbit_state", state.value())
                .param("limit", limit)
                .query((rs, n) -> new Owner(
                        rs.getString("owner_code"),
                        rs.getString("label"),
                        rs.getString("key") == null
                                ? null
                                : new OrganizationRow(
                                        rs.getString("key"),
                                        new Bilingual(rs.getString("name_en"), rs.getString("name_ja")),
                                        rs.getString("type")),
                        counts(rs)))
                .list();
        return new Snapshot(totals, countries, owners);
    }

    private static ObjectsInOrbit.Counts counts(ResultSet rs) throws SQLException {
        return new ObjectsInOrbit.Counts(
                rs.getLong("payloads"),
                rs.getLong("rocket_bodies"),
                rs.getLong("debris"),
                rs.getLong("unknown"),
                rs.getLong("total"));
    }
}
