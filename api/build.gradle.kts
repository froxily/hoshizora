import org.springframework.boot.gradle.plugin.SpringBootPlugin

plugins {
    java
    alias(libs.plugins.spring.boot)
    alias(libs.plugins.spotless)
}

group = "dev.hoshizora"
version = "0.1.0"

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(25)
    }
}

repositories {
    mavenCentral()
}

val mockitoAgent = configurations.create("mockitoAgent")

dependencies {
    implementation(platform(SpringBootPlugin.BOM_COORDINATES))
    implementation(libs.spring.boot.starter.webmvc)
    implementation(libs.spring.boot.starter.jdbc)
    implementation(libs.spring.boot.starter.actuator)
    implementation(libs.spring.boot.starter.cache)
    implementation(libs.spring.boot.starter.validation)
    implementation(libs.caffeine)
    implementation(libs.springdoc.openapi.webmvc.api)
    runtimeOnly(libs.postgresql)

    testImplementation(libs.spring.boot.starter.webmvc.test)
    testImplementation(libs.spring.boot.testcontainers)
    testImplementation(libs.testcontainers.postgresql)
    testImplementation(libs.testcontainers.junit.jupiter)
    testImplementation(libs.flyway.database.postgresql)
    testImplementation(libs.openapi.request.validator.core)
    testRuntimeOnly(libs.junit.platform.launcher)

    mockitoAgent(platform(SpringBootPlugin.BOM_COORDINATES))
    mockitoAgent(libs.mockito.core) { isTransitive = false }
}

tasks.withType<JavaCompile>().configureEach {
    options.compilerArgs.addAll(listOf("-Xlint:all", "-Werror"))
}

tasks.withType<Test>().configureEach {
    useJUnitPlatform()
    jvmArgs("-javaagent:${mockitoAgent.asPath}", "-Xshare:off")
    systemProperty("user.timezone", "UTC")
    inputs.dir("../db/migration").withPropertyName("migrations").withPathSensitivity(PathSensitivity.RELATIVE)
    inputs.dir("../facts/templates").withPropertyName("factTemplates").withPathSensitivity(PathSensitivity.RELATIVE)
    inputs.file("openapi.yaml").withPropertyName("openApiSpec").withPathSensitivity(PathSensitivity.RELATIVE)
}

tasks.test {
    systemProperty("openapi.update", "false")
}

val updateOpenApi by tasks.registering(Test::class) {
    description = "Rewrites openapi.yaml from the running application."
    group = "documentation"
    testClassesDirs = sourceSets.test.get().output.classesDirs
    classpath = sourceSets.test.get().runtimeClasspath
    filter { includeTestsMatching("dev.hoshizora.api.OpenApiSpecTest") }
    systemProperty("openapi.update", "true")
    outputs.upToDateWhen { false }
}

tasks.bootRun {
    systemProperty("user.timezone", "UTC")
    args("--spring.profiles.active=local")
}

spotless {
    java {
        palantirJavaFormat(libs.versions.palantir.java.format.get())
        forbidWildcardImports()
    }
}
