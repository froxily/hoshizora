package dev.hoshizora.api.web;

import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.jspecify.annotations.Nullable;

public record PageQuery(
        @Parameter(
                description = "1-based page number.",
                schema = @Schema(type = "integer", format = "int32", defaultValue = "1", minimum = "1"))
        @Min(1)
        Integer page,

        @Parameter(
                description = "Items per page, at most " + PageQuery.MAX_SIZE + ".",
                schema =
                        @Schema(
                                type = "integer",
                                format = "int32",
                                defaultValue = "20",
                                minimum = "1",
                                maximum = "" + PageQuery.MAX_SIZE))
        @Min(1)
        @Max(MAX_SIZE)
        Integer size) {

    public static final int MAX_SIZE = 100;
    public static final int DEFAULT_SIZE = 20;

    public PageQuery(@Nullable Integer page, @Nullable Integer size) {
        this.page = page == null ? 1 : page;
        this.size = size == null ? DEFAULT_SIZE : size;
    }

    public static PageQuery first(int size) {
        return new PageQuery(1, size);
    }

    public long offset() {
        return (page - 1L) * size;
    }
}
