package dev.hoshizora.api.facts;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import dev.hoshizora.api.i18n.Lang;
import java.util.Map;
import org.junit.jupiter.api.Test;

class FactRendererTest {

    private final FactRenderer renderer = new FactRenderer();

    @Test
    void keepsTheDecimalsTheEngineRoundedTo() {
        assertThat(renderer.render("{x, number}×", Map.of("x", 2.4), Lang.EN)).isEqualTo("2.4×");
        assertThat(renderer.render("{x}", Map.of("x", 1234567), Lang.JA)).isEqualTo("1,234,567");
    }

    @Test
    void roundsIntegersHalfUp() {
        assertThat(renderer.render("{x, number, integer}", Map.of("x", 2.5), Lang.EN))
                .isEqualTo("3");
    }

    @Test
    void formatsPercentages() {
        assertThat(renderer.render("{x, number, percent}", Map.of("x", 0.955), Lang.EN))
                .isEqualTo("95.5%");
        assertThat(renderer.render("{x, number, percent}", Map.of("x", 0.5), Lang.JA))
                .isEqualTo("50%");
    }

    @Test
    void usesManAndOkuForCompactJapaneseNumbers() {
        assertThat(renderer.render("{x, number, compact}", Map.of("x", 12550), Lang.JA))
                .isEqualTo("1.3万");
        assertThat(renderer.render("{x, number, compact}", Map.of("x", 340_000_000), Lang.JA))
                .isEqualTo("3.4億");
        assertThat(renderer.render("{x, number, compact}", Map.of("x", 12550), Lang.EN))
                .isEqualTo("12.6K");
    }

    @Test
    void formatsDatesPerLocale() {
        assertThat(renderer.render("{d, date}", Map.of("d", "2026-10-16"), Lang.JA))
                .isEqualTo("2026年10月16日");
        assertThat(renderer.render("{d, date}", Map.of("d", "2026-10-16"), Lang.EN))
                .isEqualTo("October 16, 2026");
    }

    @Test
    void picksLocalizedNamesWithEnglishFallback() {
        var params = Map.<String, Object>of("a", Map.of("en", "Japan", "ja", "日本"), "b", Map.of("en", "Polyot"));

        assertThat(renderer.render("{a}・{b}", params, Lang.JA)).isEqualTo("日本・Polyot");
        assertThat(renderer.render("{a}", params, Lang.EN)).isEqualTo("Japan");
    }

    @Test
    void refusesMissingOrMistypedParams() {
        assertThatThrownBy(() -> renderer.render("{x}", Map.of(), Lang.EN))
                .isInstanceOf(FactRenderer.FactRenderingException.class);
        assertThatThrownBy(() -> renderer.render("{x, number}", Map.of("x", "many"), Lang.EN))
                .isInstanceOf(FactRenderer.FactRenderingException.class);
    }

    @Test
    void leavesPlainTextAlone() {
        assertThat(renderer.render("No arguments here.", Map.of(), Lang.EN)).isEqualTo("No arguments here.");
    }
}
