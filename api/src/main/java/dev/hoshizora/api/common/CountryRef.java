package dev.hoshizora.api.common;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "A country or territory, named from Unicode CLDR.")
public record CountryRef(
        @Schema(description = "ISO 3166-1 alpha-2 code.", example = "JP")
        String code,

        String name) {}
