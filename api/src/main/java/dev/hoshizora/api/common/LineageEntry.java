package dev.hoshizora.api.common;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;

@Schema(description = "One source response that produced or changed this record.")
public record LineageEntry(
        @Schema(description = "Source slug, as in /api/v1/meta/sources.")
        String source,

        @Schema(description = "The request URL, or the reference file name for curated data.")
        String url,

        Instant fetchedAt,

        @Schema(description = "SHA-256 of the canonical JSON body as landed.")
        String contentHash) {}
