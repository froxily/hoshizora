package dev.hoshizora.api.web;

import java.util.List;
import java.util.function.Function;

public record Page<T>(List<T> items, int page, int size, long totalItems, int totalPages) {

    public static <T> Page<T> of(List<T> items, PageQuery query, long totalItems) {
        var totalPages = (int) ((totalItems + query.size() - 1) / query.size());
        return new Page<>(List.copyOf(items), query.page(), query.size(), totalItems, totalPages);
    }

    public <R> Page<R> map(Function<? super T, ? extends R> mapper) {
        return new Page<>(items.stream().<R>map(mapper).toList(), page, size, totalItems, totalPages);
    }
}
