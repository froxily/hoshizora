package dev.hoshizora.api.db;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import org.springframework.core.io.ClassPathResource;

public final class Sql {

    private Sql() {}

    public static String load(String path) {
        try (var in = new ClassPathResource("sql/" + path).getInputStream()) {
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException("Missing SQL file sql/" + path, e);
        }
    }
}
