package dev.hoshizora.api.neo;

import dev.hoshizora.api.i18n.Lang;
import dev.hoshizora.api.i18n.Vocabulary;
import java.util.Objects;
import java.util.regex.Pattern;
import org.jspecify.annotations.Nullable;
import org.springframework.stereotype.Component;

@Component
public final class CloseApproachViews {

    static final double DARK_ALBEDO = 0.05;
    static final double BRIGHT_ALBEDO = 0.25;

    private static final Pattern TIME_SIGMA = Pattern.compile("(<\\s*)?(?:(\\d+)_)?(\\d{2}):(\\d{2})");

    private final Vocabulary vocabulary;

    CloseApproachViews(Vocabulary vocabulary) {
        this.vocabulary = vocabulary;
    }

    public CloseApproach view(CloseApproachRow row, Lang lang) {
        return new CloseApproach(
                row.designation(),
                row.fullname(),
                Objects.requireNonNull(vocabulary.fromSource("body", row.body(), lang)),
                row.approachTdb(),
                row.approachUtc(),
                timeUncertainty(row.timeSigma()),
                row.distAu(),
                row.distKm(),
                row.distLd(),
                row.distMinKm(),
                row.distMaxKm(),
                row.vRelKms(),
                row.vInfKms(),
                row.hMag(),
                new CloseApproach.Size(
                        row.diameterKm(),
                        row.diameterSigmaKm(),
                        row.diameterMinKm(),
                        row.diameterMaxKm(),
                        DARK_ALBEDO,
                        BRIGHT_ALBEDO),
                row.sentry());
    }

    static CloseApproach.@Nullable TimeUncertainty timeUncertainty(@Nullable String sigma) {
        if (sigma == null) {
            return null;
        }
        var match = TIME_SIGMA.matcher(sigma.trim());
        if (!match.matches()) {
            return null;
        }
        var days = match.group(2) == null ? 0 : Long.parseLong(match.group(2));
        var minutes = days * 1440 + Long.parseLong(match.group(3)) * 60 + Long.parseLong(match.group(4));
        return new CloseApproach.TimeUncertainty(minutes, match.group(1) != null);
    }
}
