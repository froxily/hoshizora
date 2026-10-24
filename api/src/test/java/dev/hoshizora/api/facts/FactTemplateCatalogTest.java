package dev.hoshizora.api.facts;

import static org.assertj.core.api.Assertions.assertThat;

import dev.hoshizora.api.i18n.Lang;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import org.yaml.snakeyaml.LoaderOptions;
import org.yaml.snakeyaml.Yaml;
import org.yaml.snakeyaml.constructor.SafeConstructor;

class FactTemplateCatalogTest {

    private static final Path TEMPLATES = Path.of("..", "facts", "templates");
    private static final int MINIMUM_TEMPLATES = 25;

    private final FactRenderer renderer = new FactRenderer();

    @ParameterizedTest(name = "{0} example {1}")
    @MethodSource("examples")
    void rendersEveryExampleExactlyInEnglishAndJapanese(
            String key, int index, Map<String, Object> text, Map<String, Object> example) {
        var params = mapOf(example.get("params"));

        assertThat(renderer.render(text.get("en").toString(), params, Lang.EN))
                .as("%s en", key)
                .isEqualTo(example.get("en"));
        assertThat(renderer.render(text.get("ja").toString(), params, Lang.JA))
                .as("%s ja", key)
                .isEqualTo(example.get("ja"));
    }

    @Test
    void theCatalogHoldsAtLeastTwentyFiveTemplates() throws IOException {
        assertThat(templates()).hasSizeGreaterThanOrEqualTo(MINIMUM_TEMPLATES);
    }

    static Stream<Arguments> examples() throws IOException {
        return templates().stream().flatMap(template -> {
            var examples = listOf(template.get("examples"));
            return Stream.iterate(0, index -> index < examples.size(), index -> index + 1)
                    .map(index -> Arguments.of(
                            template.get("key"), index, mapOf(template.get("text")), mapOf(examples.get(index))));
        });
    }

    private static List<Map<String, Object>> templates() throws IOException {
        var yaml = new Yaml(new SafeConstructor(new LoaderOptions()));
        try (var files = Files.list(TEMPLATES)) {
            var paths = files.filter(path -> path.toString().endsWith(".yaml"))
                    .sorted()
                    .toList();
            var templates = new java.util.ArrayList<Map<String, Object>>();
            for (var path : paths) {
                listOf(yaml.load(Files.readString(path))).forEach(item -> templates.add(mapOf(item)));
            }
            return templates;
        }
    }

    private static List<Object> listOf(Object value) {
        assertThat(value).isInstanceOf(List.class);
        return ((List<?>) value).stream().map(Object.class::cast).toList();
    }

    private static Map<String, Object> mapOf(Object value) {
        assertThat(value).isInstanceOf(Map.class);
        return ((Map<?, ?>) value)
                .entrySet().stream()
                        .collect(Collectors.toMap(entry -> entry.getKey().toString(), Map.Entry::getValue));
    }
}
