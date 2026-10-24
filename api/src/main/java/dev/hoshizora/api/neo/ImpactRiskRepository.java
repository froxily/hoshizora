package dev.hoshizora.api.neo;

import dev.hoshizora.api.common.Lineage;
import dev.hoshizora.api.common.LineageEntry;
import dev.hoshizora.api.db.Paged;
import dev.hoshizora.api.db.Sql;
import dev.hoshizora.api.web.Page;
import dev.hoshizora.api.web.PageQuery;
import java.util.List;
import java.util.Optional;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class ImpactRiskRepository {

    static final String LIST_CACHE = "impact-risks";
    static final String DETAIL_CACHE = "impact-risk";

    private static final String LIST = Sql.load("neo/impact_risks.sql");

    private final JdbcClient jdbc;
    private final CloseApproachRepository approaches;
    private final Lineage lineage;

    ImpactRiskRepository(JdbcClient jdbc, CloseApproachRepository approaches, Lineage lineage) {
        this.jdbc = jdbc;
        this.approaches = approaches;
        this.lineage = lineage;
    }

    @Cacheable(LIST_CACHE)
    public Page<ImpactRiskRow> list(ImpactRiskQuery query, PageQuery paging) {
        var statement = jdbc.sql(LIST)
                .param("designation", query.designation())
                .param("include_removed", query.includeRemoved())
                .param("min_palermo", query.minPalermo())
                .param("min_torino", query.minTorino())
                .param("sort", query.sort().value());
        return Paged.fetch(statement, paging, "designation", (rs, n) -> ImpactRiskRow.of(rs));
    }

    @Cacheable(DETAIL_CACHE)
    public Optional<Detail> detail(String designation) {
        return list(ImpactRiskQuery.of(designation), PageQuery.first(1)).items().stream()
                .findFirst()
                .map(risk -> new Detail(
                        risk,
                        approaches
                                .list(CloseApproachFilter.of(designation), PageQuery.first(PageQuery.MAX_SIZE))
                                .items(),
                        lineage.of("core.impact_risk", designation)));
    }

    record Detail(ImpactRiskRow risk, List<CloseApproachRow> approaches, List<LineageEntry> lineage) {}
}
