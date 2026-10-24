package dev.hoshizora.api.web;

import io.swagger.v3.core.util.Json;
import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.Operation;
import io.swagger.v3.oas.models.examples.Example;
import io.swagger.v3.oas.models.headers.Header;
import io.swagger.v3.oas.models.media.ArraySchema;
import io.swagger.v3.oas.models.media.Content;
import io.swagger.v3.oas.models.media.IntegerSchema;
import io.swagger.v3.oas.models.media.MediaType;
import io.swagger.v3.oas.models.media.ObjectSchema;
import io.swagger.v3.oas.models.media.Schema;
import io.swagger.v3.oas.models.media.StringSchema;
import io.swagger.v3.oas.models.parameters.HeaderParameter;
import io.swagger.v3.oas.models.parameters.Parameter;
import io.swagger.v3.oas.models.responses.ApiResponse;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.util.List;
import java.util.Map;
import org.springdoc.core.customizers.OpenApiCustomizer;
import org.springframework.core.io.ClassPathResource;

final class ApiConventions implements OpenApiCustomizer {

    private static final String PROBLEM_JSON = "application/problem+json";

    @Override
    public void customise(OpenAPI openApi) {
        addComponents(
                openApi.getComponents() == null
                        ? openApi.components(new Components()).getComponents()
                        : openApi.getComponents());
        if (openApi.getPaths() == null) {
            return;
        }
        openApi.getPaths().forEach((path, item) -> {
            if (item.getGet() != null) {
                document(path, item.getGet());
            }
        });
    }

    private static void document(String path, Operation operation) {
        operation.addParametersItem(new Parameter().$ref("#/components/parameters/AcceptLanguage"));
        operation.addParametersItem(new Parameter().$ref("#/components/parameters/IfNoneMatch"));
        var responses = operation.getResponses();
        var ok = responses.get("200");
        if (ok != null) {
            ok.headers(Map.of(
                    "ETag", new Header().$ref("#/components/headers/ETag"),
                    "Cache-Control", new Header().$ref("#/components/headers/CacheControl"),
                    "Content-Language", new Header().$ref("#/components/headers/ContentLanguage")));
            attachExample(operation.getOperationId(), ok);
        }
        responses.addApiResponse("304", new ApiResponse().$ref("#/components/responses/NotModified"));
        responses.addApiResponse("400", new ApiResponse().$ref("#/components/responses/BadRequest"));
        if (path.contains("{")) {
            responses.addApiResponse("404", new ApiResponse().$ref("#/components/responses/NotFound"));
        }
        responses.addApiResponse("500", new ApiResponse().$ref("#/components/responses/InternalError"));
    }

    private static void attachExample(String operationId, ApiResponse ok) {
        var resource = new ClassPathResource("openapi/examples/" + operationId + ".json");
        if (!resource.exists() || ok.getContent() == null) {
            return;
        }
        try (var in = resource.getInputStream()) {
            var example = new Example().value(Json.mapper().readTree(in));
            ok.getContent().values().forEach(media -> media.setExamples(Map.of("seed", example)));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static void addComponents(Components components) {
        components
                .addParameters(
                        "AcceptLanguage",
                        new HeaderParameter()
                                .name("Accept-Language")
                                .description("Language for localized text: en (default) or ja. Region"
                                        + " subtags and q-values are honored, e.g. ja-JP,ja;q=0.9.")
                                .schema(new StringSchema()._default("en").example("ja")))
                .addParameters(
                        "IfNoneMatch",
                        new HeaderParameter()
                                .name("If-None-Match")
                                .description("An ETag from an earlier response; a match returns 304 with no body.")
                                .schema(new StringSchema()))
                .addHeaders(
                        "ETag",
                        new Header()
                                .description("Strong validator: a hash of this exact response body.")
                                .schema(new StringSchema()))
                .addHeaders(
                        "CacheControl",
                        new Header()
                                .description("public, max-age matched to the source's update cadence.")
                                .schema(new StringSchema()))
                .addHeaders(
                        "ContentLanguage",
                        new Header()
                                .description("The language the response was localized to: en or ja.")
                                .schema(new StringSchema()._enum(List.of("en", "ja"))))
                .addSchemas("Problem", problemSchema())
                .addResponses(
                        "NotModified",
                        new ApiResponse().description("Not modified: the If-None-Match ETag still matches."))
                .addResponses("BadRequest", problem("A query or path parameter is invalid."))
                .addResponses("NotFound", problem("No resource exists with this identifier."))
                .addResponses("InternalError", problem("Unexpected error. No internal details are exposed."));
    }

    private static ApiResponse problem(String description) {
        return new ApiResponse()
                .description(description)
                .content(new Content()
                        .addMediaType(
                                PROBLEM_JSON,
                                new MediaType().schema(new Schema<>().$ref("#/components/schemas/Problem"))));
    }

    private static Schema<?> problemSchema() {
        var invalidParameter = new ObjectSchema();
        invalidParameter.addProperty("parameter", new StringSchema().description("The query or path parameter name."));
        invalidParameter.addProperty(
                "message", new StringSchema().description("Why the value was rejected, localized."));
        invalidParameter.setRequired(List.of("parameter", "message"));
        var problem = new ObjectSchema();
        problem.description("RFC 9457 Problem Details. title and detail are localized by Accept-Language.");
        problem.addProperty("type", new StringSchema().description("Omitted when about:blank."));
        problem.addProperty("title", new StringSchema());
        problem.addProperty("status", new IntegerSchema());
        problem.addProperty("detail", new StringSchema());
        problem.addProperty("instance", new StringSchema());
        problem.addProperty(
                "code",
                new StringSchema()
                        ._enum(List.of(
                                "invalid_parameter",
                                "not_found",
                                "method_not_allowed",
                                "not_acceptable",
                                "internal_error")));
        problem.addProperty("errors", new ArraySchema().items(invalidParameter));
        problem.setRequired(List.of("title", "status", "code"));
        return problem;
    }
}
