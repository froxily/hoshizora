package dev.hoshizora.api.web;

import java.util.Arrays;
import org.springframework.core.convert.converter.Converter;
import org.springframework.core.convert.converter.ConverterFactory;

final class ApiValueConverterFactory implements ConverterFactory<String, ApiValue> {

    @Override
    public <T extends ApiValue> Converter<String, T> getConverter(Class<T> targetType) {
        return source -> Arrays.stream(targetType.getEnumConstants())
                .filter(constant -> constant.value().equals(source))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Unknown value: " + source));
    }
}
