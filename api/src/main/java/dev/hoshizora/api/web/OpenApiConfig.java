package dev.hoshizora.api.web;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.servers.Server;
import java.util.List;
import org.springdoc.core.customizers.OpenApiCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration(proxyBeanMethods = false)
class OpenApiConfig {

    @Bean
    OpenAPI hoshizoraOpenApi() {
        return new OpenAPI()
                .info(new Info()
                        .title("Hoshizora API")
                        .version("v1")
                        .description("Read-only space data analytics in English and Japanese. Localized text follows"
                                + " Accept-Language (en or ja), and each localized field has a sibling *_lang field"
                                + " naming the language actually returned, because some names exist only in English."))
                .servers(List.of(new Server().url("/")));
    }

    @Bean
    RecordSchemas recordSchemas() {
        return new RecordSchemas();
    }

    @Bean
    OpenApiCustomizer apiConventions() {
        return new ApiConventions();
    }
}
