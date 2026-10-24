package dev.hoshizora.api.exoplanets;

import dev.hoshizora.api.common.LineageEntry;
import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

@Schema(description = "One exoplanet and the archive responses behind its record.")
public record ExoplanetDetail(Exoplanet planet, List<LineageEntry> lineage) {}
