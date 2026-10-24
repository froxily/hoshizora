package dev.hoshizora.api.facts;

import static org.assertj.core.api.Assertions.assertThat;

import dev.hoshizora.api.i18n.Bilingual;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class FactMixTest {

    private static FactRow fact(long id, String module, double score) {
        return new FactRow(
                id,
                module + ".template",
                module,
                new Bilingual("text", "テキスト"),
                null,
                null,
                Map.of(),
                score,
                "computed",
                List.of(),
                null,
                Instant.EPOCH,
                null);
    }

    private static List<Long> ids(List<FactRow> rows) {
        return rows.stream().map(FactRow::id).toList();
    }

    @Test
    void putsEveryModulesBestFactBeforeAnySecondBest() {
        var bestFirst = List.of(
                fact(1, "agencies", 1.0),
                fact(2, "agencies", 1.0),
                fact(3, "agencies", 1.0),
                fact(4, "launches", 0.9),
                fact(5, "near-earth", 0.8),
                fact(6, "launches", 0.7),
                fact(7, "space-weather", 0.5));

        assertThat(ids(FactMix.acrossModules(bestFirst))).containsExactly(1L, 4L, 5L, 7L, 2L, 6L, 3L);
    }

    @Test
    void keepsTheScoreOrderInsideEachRound() {
        var bestFirst = List.of(fact(1, "sun", 0.9), fact(2, "launches", 0.8), fact(3, "sun", 0.7));

        assertThat(ids(FactMix.acrossModules(bestFirst))).containsExactly(1L, 2L, 3L);
    }

    @Test
    void handlesNoFacts() {
        assertThat(FactMix.acrossModules(List.of())).isEmpty();
    }
}
