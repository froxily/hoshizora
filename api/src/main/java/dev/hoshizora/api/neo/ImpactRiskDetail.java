package dev.hoshizora.api.neo;

import dev.hoshizora.api.common.LineageEntry;
import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

@Schema(description = "A Sentry object with every close approach JPL lists for it and the source lineage.")
public record ImpactRiskDetail(
        ImpactRisk risk,

        @Schema(description = "Its close approaches within 0.05 au from 1900 to 2200, soonest first, at most 100.")
        List<CloseApproach> closeApproaches,

        List<LineageEntry> lineage) {}
