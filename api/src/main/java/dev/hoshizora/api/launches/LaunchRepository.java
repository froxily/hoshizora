package dev.hoshizora.api.launches;

import dev.hoshizora.api.common.Lineage;
import dev.hoshizora.api.common.OrganizationRow;
import dev.hoshizora.api.db.Paged;
import dev.hoshizora.api.db.Rows;
import dev.hoshizora.api.db.Sql;
import dev.hoshizora.api.i18n.Bilingual;
import dev.hoshizora.api.web.Page;
import dev.hoshizora.api.web.PageQuery;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.jspecify.annotations.Nullable;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class LaunchRepository {

    static final String LIST_CACHE = "launches";
    static final String DETAIL_CACHE = "launch";
    static final int OBJECT_LIMIT = 100;

    private static final String LIST = Sql.load("launches/list.sql");
    private static final String DETAIL = Sql.load("launches/detail.sql");
    private static final String PROGRAMS = Sql.load("launches/programs.sql");
    private static final String PARTNERS = Sql.load("launches/partners.sql");
    private static final String OBJECTS = Sql.load("launches/objects.sql");

    private final JdbcClient jdbc;
    private final Lineage lineage;

    LaunchRepository(JdbcClient jdbc, Lineage lineage) {
        this.jdbc = jdbc;
        this.lineage = lineage;
    }

    @Cacheable(LIST_CACHE)
    public Page<LaunchRow> list(LaunchFilter filter, PageQuery query) {
        var statement = jdbc.sql(LIST)
                .param("from", timestamp(filter.from()))
                .param("to", timestamp(filter.to()))
                .param(
                        "status",
                        filter.status() == null ? null : filter.status().value())
                .param("provider", filter.provider())
                .param("program", filter.program())
                .param("vehicle_family", filter.vehicleFamily())
                .param("site_country", filter.siteCountry())
                .param("pad", filter.pad())
                .param("sort", filter.sort().value());
        return Paged.fetch(statement, query, "launch_id", (rs, n) -> LaunchRows.summary(rs));
    }

    @Cacheable(DETAIL_CACHE)
    public Optional<LaunchDetailRow> detail(UUID id) {
        return jdbc.sql(DETAIL)
                .param("id", id)
                .query((rs, n) -> new Core(
                        LaunchRows.summary(rs),
                        Rows.instant(rs, "window_start"),
                        Rows.instant(rs, "window_end"),
                        rs.getString("failure_reason")))
                .optional()
                .map(this::withRelations);
    }

    private LaunchDetailRow withRelations(Core core) {
        var launch = core.launch();
        var designator = launch.launchDesignator();
        var objects = designator == null ? List.<CountedObject>of() : objects(designator);
        var organizationId = launch.providerOrganizationId();
        var mission = launch.mission();
        return new LaunchDetailRow(
                launch,
                core.windowStart(),
                core.windowEnd(),
                core.failureReason(),
                organizationId == null ? List.of() : programs(organizationId),
                mission == null ? List.of() : partners(mission.id()),
                objects.stream().map(CountedObject::object).toList(),
                objects.isEmpty() ? 0 : objects.getFirst().total(),
                lineage.of("core.launch", launch.id().toString()));
    }

    private List<LaunchDetailRow.Program> programs(long organizationId) {
        return jdbc.sql(PROGRAMS)
                .param("organization_id", organizationId)
                .query((rs, n) -> new LaunchDetailRow.Program(
                        rs.getString("slug"), new Bilingual(rs.getString("name_en"), rs.getString("name_ja"))))
                .list();
    }

    private List<OrganizationRow> partners(int missionId) {
        return jdbc.sql(PARTNERS)
                .param("mission_id", missionId)
                .query((rs, n) -> new OrganizationRow(
                        rs.getString("key"),
                        new Bilingual(rs.getString("name_en"), rs.getString("name_ja")),
                        rs.getString("type")))
                .list();
    }

    private List<CountedObject> objects(String designator) {
        return jdbc.sql(OBJECTS)
                .param("designator", designator)
                .param("limit", OBJECT_LIMIT)
                .query((rs, n) -> new CountedObject(
                        new LaunchDetailRow.SpaceObject(
                                rs.getInt("norad_id"),
                                rs.getString("object_id"),
                                rs.getString("name"),
                                rs.getString("object_type"),
                                rs.getString("orbit_state"),
                                rs.getString("owner_code"),
                                Rows.date(rs, "decay_date")),
                        rs.getLong("total")))
                .list();
    }

    private static @Nullable Timestamp timestamp(@Nullable Instant instant) {
        return instant == null ? null : Timestamp.from(instant);
    }

    private record Core(
            LaunchRow launch,
            @Nullable Instant windowStart,
            @Nullable Instant windowEnd,
            @Nullable String failureReason) {}

    private record CountedObject(LaunchDetailRow.SpaceObject object, long total) {}
}
