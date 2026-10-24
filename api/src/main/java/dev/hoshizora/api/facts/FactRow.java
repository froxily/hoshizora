package dev.hoshizora.api.facts;

import dev.hoshizora.api.i18n.Bilingual;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.jspecify.annotations.Nullable;

record FactRow(
        long id,
        String templateKey,
        String module,
        Bilingual text,
        @Nullable String entityType,
        @Nullable String entityKey,
        Map<String, Object> params,
        double score,
        String kind,
        List<SourceRef> sourceRefs,
        @Nullable String citationUrl,
        Instant generatedAt,
        @Nullable Instant validUntil) {

    record SourceRef(String entity, String key) {}

    boolean validAt(Instant now) {
        return validUntil == null || validUntil.isAfter(now);
    }
}
