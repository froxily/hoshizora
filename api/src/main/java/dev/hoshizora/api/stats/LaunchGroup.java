package dev.hoshizora.api.stats;

import dev.hoshizora.api.i18n.Lang;
import io.swagger.v3.oas.annotations.media.Schema;

@Schema(
        description = "A launch grouping: all launches, a national program, a provider, a vehicle family or a"
                + " launch-site country.")
public record LaunchGroup(
        LaunchGrouping kind,

        @Schema(description = "Program slug, provider key, vehicle family or ISO country code.", example = "japan")
        String key,

        String name,
        Lang nameLang) {}
