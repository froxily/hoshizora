package dev.hoshizora.api.facts;

import dev.hoshizora.api.i18n.Lang;
import dev.hoshizora.api.i18n.Term;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.jspecify.annotations.Nullable;

@Schema(
        description =
                "A fun fact computed from ingested data, or curated with a citation, rendered for Accept-Language.")
public record Fact(
        long id,

        @Schema(description = "Template key.", example = "near-earth.closest_this_week")
        String key,

        @Schema(description = "The page it belongs to, e.g. home, launches, near-earth, sun or agencies.")
        String module,

        String text,
        Lang textLang,

        @Schema(description = "The numbers and names in the text, unformatted, so the data stays inspectable.")
        Map<String, Object> params,

        @Schema(description = "How extreme or novel the fact is; higher shows first.")
        double score,

        @Schema(description = "computed or curated.") Term kind,

        @Schema(description = "Required for curated facts: where the fact is documented.") @Nullable
        String citationUrl,

        @Nullable Entity entity,

        @Schema(description = "The records behind the fact, linked to the API where a route exists.")
        List<Reference> sources,

        Instant generatedAt,
        @Nullable Instant validUntil) {

    @Schema(name = "FactEntity", description = "The record the fact is about.")
    public record Entity(String type, String key) {}

    @Schema(name = "FactReference")
    public record Reference(
            @Schema(example = "core.close_approach") String entity,
            String key,

            @Schema(description = "API route for the record, where one exists.") @Nullable
            String recordsUrl) {}
}
