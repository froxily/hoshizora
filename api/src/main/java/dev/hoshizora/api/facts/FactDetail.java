package dev.hoshizora.api.facts;

import dev.hoshizora.api.common.LineageEntry;
import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

@Schema(description = "A fact with the source responses behind every record it uses: how we know this.")
public record FactDetail(Fact fact, List<LineageEntry> lineage) {}
