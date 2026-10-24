package dev.hoshizora.api.support;

import static org.assertj.core.api.Assertions.assertThat;

import com.atlassian.oai.validator.OpenApiInteractionValidator;
import com.atlassian.oai.validator.model.Request;
import com.atlassian.oai.validator.model.SimpleResponse;
import java.io.UnsupportedEncodingException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import org.springframework.test.web.servlet.assertj.MvcTestResult;

public final class OpenApiContract {

    public static final Path SPEC = Path.of("openapi.yaml");

    private OpenApiContract() {}

    public static void assertConforms(MvcTestResult result) {
        var request = result.getMvcResult().getRequest();
        var response = result.getResponse();
        var builder = SimpleResponse.Builder.status(response.getStatus()).withBody(body(result));
        response.getHeaderNames().forEach(name -> builder.withHeader(name, response.getHeaders(name)));
        var report = Validator.INSTANCE.validateResponse(
                request.getRequestURI(), Request.Method.valueOf(request.getMethod()), builder.build());
        assertThat(report.getMessages())
                .as("response to %s %s conforms to %s", request.getMethod(), request.getRequestURI(), SPEC)
                .isEmpty();
    }

    private static String body(MvcTestResult result) {
        try {
            return result.getResponse().getContentAsString(StandardCharsets.UTF_8);
        } catch (UnsupportedEncodingException e) {
            throw new IllegalStateException(e);
        }
    }

    private static final class Validator {

        private static final OpenApiInteractionValidator INSTANCE =
                OpenApiInteractionValidator.createForSpecificationUrl(
                                SPEC.toUri().toString())
                        .build();
    }
}
