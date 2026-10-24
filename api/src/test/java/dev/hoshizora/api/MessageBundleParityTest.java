package dev.hoshizora.api;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.Properties;
import java.util.Set;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import org.junit.jupiter.api.Test;
import org.springframework.core.io.ClassPathResource;

class MessageBundleParityTest {

    private static final Pattern PLACEHOLDER = Pattern.compile("\\{\\d+}");

    private final Map<String, String> en = load("i18n/messages.properties");
    private final Map<String, String> ja = load("i18n/messages_ja.properties");

    @Test
    void everyKeyExistsInBothLanguages() {
        assertThat(ja.keySet()).containsExactlyInAnyOrderElementsOf(en.keySet());
    }

    @Test
    void translationsUseTheSamePlaceholders() {
        en.forEach((key, text) ->
                assertThat(placeholders(ja.getOrDefault(key, ""))).as(key).isEqualTo(placeholders(text)));
    }

    @Test
    void noTranslationIsBlank() {
        assertThat(en).allSatisfy((key, text) -> assertThat(text).as(key).isNotBlank());
        assertThat(ja).allSatisfy((key, text) -> assertThat(text).as(key).isNotBlank());
    }

    private static Set<String> placeholders(String text) {
        return PLACEHOLDER.matcher(text).results().map(match -> match.group()).collect(Collectors.toSet());
    }

    private static Map<String, String> load(String path) {
        var properties = new Properties();
        try (var reader = new InputStreamReader(new ClassPathResource(path).getInputStream(), StandardCharsets.UTF_8)) {
            properties.load(reader);
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
        return properties.stringPropertyNames().stream().collect(Collectors.toMap(key -> key, properties::getProperty));
    }
}
