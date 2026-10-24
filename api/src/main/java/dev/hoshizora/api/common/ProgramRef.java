package dev.hoshizora.api.common;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "A national space program grouping its agencies, companies and armed forces.")
public record ProgramRef(@Schema(example = "japan") String slug, String name) {}
