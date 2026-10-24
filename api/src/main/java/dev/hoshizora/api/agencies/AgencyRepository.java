package dev.hoshizora.api.agencies;

import dev.hoshizora.api.common.Lineage;
import dev.hoshizora.api.common.OrganizationRow;
import dev.hoshizora.api.db.Paged;
import dev.hoshizora.api.db.Rows;
import dev.hoshizora.api.db.Sql;
import dev.hoshizora.api.i18n.Bilingual;
import dev.hoshizora.api.launches.LaunchRow;
import dev.hoshizora.api.launches.LaunchRows;
import dev.hoshizora.api.web.Page;
import dev.hoshizora.api.web.PageQuery;
import java.util.List;
import java.util.Optional;
import org.jspecify.annotations.Nullable;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class AgencyRepository {

    static final String LIST_CACHE = "agencies";
    static final String DETAIL_CACHE = "agency";

    private static final String LIST = Sql.load("agencies/list.sql");
    private static final String DETAIL = Sql.load("agencies/detail.sql");
    private static final String RELATED = Sql.load("agencies/related.sql");
    private static final String VEHICLES = Sql.load("agencies/vehicles.sql");
    private static final String RECENT_LAUNCHES = Sql.load("agencies/recent_launches.sql");
    private static final String NEXT_LAUNCH = Sql.load("agencies/next_launch.sql");
    private static final String RELIABILITY = Sql.load("agencies/reliability.sql");
    private static final String OBJECTS = Sql.load("agencies/objects.sql");
    private static final String PARTNER_MISSIONS = Sql.load("agencies/partner_missions.sql");

    private final JdbcClient jdbc;
    private final Lineage lineage;

    AgencyRepository(JdbcClient jdbc, Lineage lineage) {
        this.jdbc = jdbc;
        this.lineage = lineage;
    }

    @Cacheable(LIST_CACHE)
    public Page<AgencyRow> list(AgencyFilter filter, PageQuery query) {
        var statement = jdbc.sql(LIST)
                .param("type", filter.type() == null ? null : filter.type().value())
                .param("country", filter.country())
                .param("program", filter.program())
                .param("has_launches", filter.hasLaunches())
                .param("q", filter.query())
                .param("sort", filter.sort().value());
        return Paged.fetch(statement, query, "id", (rs, n) -> AgencyRow.of(rs));
    }

    @Cacheable(DETAIL_CACHE)
    public Optional<AgencyDetailRow> detail(String key) {
        return jdbc.sql(DETAIL)
                .param("key", key)
                .query((rs, n) -> AgencyRow.of(rs))
                .optional()
                .map(this::withRelations);
    }

    private AgencyDetailRow withRelations(AgencyRow profile) {
        var related = related(profile);
        var parent = related.stream()
                .filter(Related::parent)
                .map(Related::organization)
                .findFirst()
                .orElse(null);
        var members = related.stream()
                .filter(organization -> !organization.parent())
                .map(Related::organization)
                .toList();
        return new AgencyDetailRow(
                profile,
                parent,
                members,
                vehicles(profile.id()),
                launches(RECENT_LAUNCHES, profile.id()),
                launches(NEXT_LAUNCH, profile.id()).stream().findFirst().orElse(null),
                reliability(profile.key()),
                objects(profile.id()),
                jdbc.sql(PARTNER_MISSIONS)
                        .param("id", profile.id())
                        .query(Long.class)
                        .single(),
                lineage.of("core.organization", Long.toString(profile.id())));
    }

    private List<Related> related(AgencyRow profile) {
        return jdbc.sql(RELATED)
                .param("id", profile.id())
                .param("parent_id", profile.parentId())
                .query((rs, n) -> new Related(
                        new OrganizationRow(
                                rs.getString("key"),
                                new Bilingual(rs.getString("name_en"), rs.getString("name_ja")),
                                rs.getString("type")),
                        rs.getBoolean("is_parent")))
                .list();
    }

    private List<AgencyDetailRow.VehicleUsage> vehicles(long id) {
        return jdbc.sql(VEHICLES)
                .param("id", id)
                .query((rs, n) -> new AgencyDetailRow.VehicleUsage(
                        rs.getInt("vehicle_id"),
                        new Bilingual(rs.getString("name"), rs.getString("name_ja")),
                        rs.getString("family"),
                        rs.getLong("attempts"),
                        rs.getLong("successes")))
                .list();
    }

    private List<LaunchRow> launches(String sql, long id) {
        return jdbc.sql(sql)
                .param("id", id)
                .query((rs, n) -> LaunchRows.summary(rs))
                .list();
    }

    private AgencyDetailRow.@Nullable Reliability reliability(String key) {
        return jdbc.sql(RELIABILITY)
                .param("key", key)
                .query((rs, n) -> {
                    var attempts = Rows.integer(rs, "recent_attempts");
                    return attempts == null
                            ? null
                            : new AgencyDetailRow.Reliability(
                                    attempts,
                                    rs.getInt("recent_successes"),
                                    rs.getInt("current_streak"),
                                    rs.getInt("longest_streak"));
                })
                .optional()
                .orElse(null);
    }

    private AgencyDetailRow.@Nullable CataloguedObjects objects(long id) {
        return jdbc.sql(OBJECTS)
                .param("id", id)
                .query((rs, n) -> {
                    var codes = Rows.strings(rs, "owner_codes");
                    return codes.isEmpty()
                            ? null
                            : new AgencyDetailRow.CataloguedObjects(
                                    codes,
                                    rs.getLong("in_earth_orbit"),
                                    rs.getLong("payloads_in_earth_orbit"),
                                    rs.getLong("beyond_earth"),
                                    rs.getLong("decayed"));
                })
                .optional()
                .orElse(null);
    }

    private record Related(OrganizationRow organization, boolean parent) {}
}
