package dev.hoshizora.api.web;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import io.swagger.v3.core.converter.AnnotatedType;
import io.swagger.v3.core.converter.ModelConverter;
import io.swagger.v3.core.converter.ModelConverterContext;
import io.swagger.v3.core.jackson.ModelResolver;
import io.swagger.v3.core.util.Json;
import io.swagger.v3.oas.models.media.Schema;
import java.util.Arrays;
import java.util.Iterator;
import org.jspecify.annotations.Nullable;

final class RecordSchemas extends ModelResolver {

    private static final PropertyNamingStrategies.SnakeCaseStrategy SNAKE_CASE =
            new PropertyNamingStrategies.SnakeCaseStrategy();

    RecordSchemas() {
        super(Json.mapper().copy().setPropertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE));
        openapi31(true);
    }

    @Override
    @SuppressWarnings({"rawtypes", "unchecked"})
    public Schema resolve(AnnotatedType annotatedType, ModelConverterContext context, Iterator<ModelConverter> next) {
        var schema = super.resolve(annotatedType, context, next);
        var type = _mapper.constructType(annotatedType.getType()).getRawClass();
        if (schema == null || !type.isRecord()) {
            return schema;
        }
        var definition = schema.get$ref() == null
                ? schema
                : context.getDefinedModels()
                        .get(schema.get$ref().substring(schema.get$ref().lastIndexOf('/') + 1));
        if (definition != null && definition.getProperties() != null) {
            var required = Arrays.stream(type.getRecordComponents())
                    .filter(component -> !component.getAnnotatedType().isAnnotationPresent(Nullable.class))
                    .map(component -> SNAKE_CASE.translate(component.getName()))
                    .filter(definition.getProperties()::containsKey)
                    .sorted()
                    .toList();
            definition.setRequired(required.isEmpty() ? null : required);
        }
        return schema;
    }
}
