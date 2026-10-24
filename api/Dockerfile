FROM eclipse-temurin:25.0.4.1_1-jdk-noble AS build
WORKDIR /workspace
COPY gradlew settings.gradle.kts build.gradle.kts gradle.properties ./
COPY gradle gradle
RUN ./gradlew --no-daemon --quiet dependencies > /dev/null
COPY openapi.yaml ./
COPY src src
RUN ./gradlew --no-daemon --quiet bootJar -x test \
    && java -Djarmode=tools -jar build/libs/*.jar extract --destination /app

FROM eclipse-temurin:25.0.4.1_1-jre-noble
RUN useradd --system --uid 10001 --create-home --home-dir /app hoshizora
WORKDIR /app
COPY --from=build --chown=hoshizora /app ./
USER hoshizora
RUN java -XX:AOTCacheOutput=app.aot \
        -Dspring.context.exit=onRefresh \
        -Dspring.profiles.active=preview \
        -Dspring.datasource.url=jdbc:postgresql://localhost:5432/training \
        -jar *.jar
ENV JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=70 -XX:+UseSerialGC -XX:TieredStopAtLevel=1 -Xss512k"
EXPOSE 8080
ENTRYPOINT ["sh", "-c", "exec java -XX:AOTCache=app.aot -Dspring.profiles.active=preview -jar /app/*.jar"]
