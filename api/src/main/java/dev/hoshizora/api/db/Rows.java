package dev.hoshizora.api.db;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.util.Arrays;
import java.util.List;
import org.jspecify.annotations.Nullable;

public final class Rows {

    private Rows() {}

    public static @Nullable Instant instant(ResultSet rs, String column) throws SQLException {
        var value = rs.getObject(column, OffsetDateTime.class);
        return value == null ? null : value.toInstant();
    }

    public static @Nullable LocalDateTime localDateTime(ResultSet rs, String column) throws SQLException {
        return rs.getObject(column, LocalDateTime.class);
    }

    public static @Nullable LocalDate date(ResultSet rs, String column) throws SQLException {
        return rs.getObject(column, LocalDate.class);
    }

    public static @Nullable Double decimal(ResultSet rs, String column) throws SQLException {
        var value = rs.getDouble(column);
        return rs.wasNull() ? null : value;
    }

    public static @Nullable Long whole(ResultSet rs, String column) throws SQLException {
        var value = rs.getLong(column);
        return rs.wasNull() ? null : value;
    }

    public static @Nullable Integer integer(ResultSet rs, String column) throws SQLException {
        var value = rs.getInt(column);
        return rs.wasNull() ? null : value;
    }

    public static @Nullable Boolean bool(ResultSet rs, String column) throws SQLException {
        var value = rs.getBoolean(column);
        return rs.wasNull() ? null : value;
    }

    public static List<String> strings(ResultSet rs, String column) throws SQLException {
        var array = rs.getArray(column);
        if (array == null) {
            return List.of();
        }
        return Arrays.stream((Object[]) array.getArray())
                .map(String.class::cast)
                .toList();
    }
}
