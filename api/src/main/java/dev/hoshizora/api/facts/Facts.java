package dev.hoshizora.api.facts;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

@Schema(description = "The highest-scoring current facts, best first.")
public record Facts(List<Fact> items) {}
