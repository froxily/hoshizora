package dev.hoshizora.api;

import static org.assertj.core.api.Assertions.assertThat;

import com.atlassian.oai.validator.OpenApiInteractionValidator;
import com.atlassian.oai.validator.model.Request;
import com.atlassian.oai.validator.model.SimpleResponse;
import dev.hoshizora.api.support.ApiTest;
import dev.hoshizora.api.support.OpenApiContract;
import io.swagger.v3.core.util.Json;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.Operation;
import io.swagger.v3.parser.OpenAPIV3Parser;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.function.BiConsumer;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.web.servlet.assertj.MockMvcTester;

@ApiTest
class OpenApiSpecTest {

    private final MockMvcTester mvc;

    @Autowired
    OpenApiSpecTest(MockMvcTester mvc) {
        this.mvc = mvc;
    }

    @Test
    void committedSpecMatchesTheApplication() throws IOException {
        var live = liveSpec();
        if (Boolean.getBoolean("openapi.update")) {
            Files.writeString(OpenApiContract.SPEC, live, StandardCharsets.UTF_8);
        }
        assertThat(live)
                .as("%s is stale: run ./gradlew updateOpenApi", OpenApiContract.SPEC)
                .isEqualTo(Files.readString(OpenApiContract.SPEC, StandardCharsets.UTF_8));
    }

    @Test
    void everyOperationIsFullyDocumented() {
        forEachOperation(parsed(), (path, operation) -> {
            assertThat(operation.getSummary()).as("%s summary", path).isNotBlank();
            assertThat(operation.getDescription()).as("%s description", path).isNotBlank();
            operation.getParameters().stream()
                    .filter(parameter -> parameter.get$ref() == null)
                    .forEach(parameter -> assertThat(parameter.getDescription())
                            .as("%s parameter %s", path, parameter.getName())
                            .isNotBlank());
            var ok = operation.getResponses().get("200");
            assertThat(ok).as("%s 200 response", path).isNotNull();
            assertThat(ok.getContent().get("application/json").getExamples())
                    .as("%s example", path)
                    .isNotEmpty();
            assertThat(operation.getResponses()).as("%s responses", path).containsKeys("304", "400", "500");
            if (path.contains("{")) {
                assertThat(operation.getResponses()).as("%s responses", path).containsKey("404");
            }
        });
    }

    @Test
    void everyExampleConformsToItsSchema() {
        var validator = OpenApiInteractionValidator.createForInlineApiSpecification(liveSpec())
                .build();
        forEachOperation(parsed(), (path, operation) -> {
            var media = operation.getResponses().get("200").getContent().get("application/json");
            media.getExamples().forEach((name, example) -> {
                var response = SimpleResponse.Builder.ok()
                        .withContentType("application/json")
                        .withBody(Json.pretty(example.getValue()))
                        .build();
                var concretePath = path.replaceAll("\\{[^}]+}", "example");
                var report = validator.validateResponse(concretePath, Request.Method.GET, response);
                assertThat(report.getMessages()).as("%s example %s", path, name).isEmpty();
            });
        });
    }

    private OpenAPI parsed() {
        return new OpenAPIV3Parser().readContents(liveSpec()).getOpenAPI();
    }

    private String liveSpec() {
        var result = mvc.get().uri("/v3/api-docs.yaml").exchange();
        assertThat(result).hasStatusOk();
        try {
            return result.getResponse().getContentAsString(StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
    }

    private static void forEachOperation(OpenAPI openApi, BiConsumer<String, Operation> check) {
        if (openApi.getPaths() == null) {
            return;
        }
        openApi.getPaths().forEach((path, item) -> item.readOperations().forEach(op -> check.accept(path, op)));
    }
}
