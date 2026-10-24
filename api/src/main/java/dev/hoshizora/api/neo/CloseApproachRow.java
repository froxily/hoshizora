package dev.hoshizora.api.neo;

import dev.hoshizora.api.db.Rows;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.time.LocalDateTime;
import java.util.Objects;
import org.jspecify.annotations.Nullable;

public record CloseApproachRow(
        String designation,
        @Nullable String fullname,
        String body,
        LocalDateTime approachTdb,
        @Nullable Instant approachUtc,
        @Nullable String timeSigma,
        double distAu,
        double distKm,
        double distLd,
        @Nullable Double distMinKm,
        @Nullable Double distMaxKm,
        @Nullable Double vRelKms,
        @Nullable Double vInfKms,
        @Nullable Double hMag,
        @Nullable Double diameterKm,
        @Nullable Double diameterSigmaKm,
        @Nullable Double diameterMinKm,
        @Nullable Double diameterMaxKm,
        boolean sentry) {

    public static CloseApproachRow of(ResultSet rs) throws SQLException {
        return new CloseApproachRow(
                rs.getString("designation"),
                rs.getString("fullname"),
                rs.getString("body"),
                Objects.requireNonNull(Rows.localDateTime(rs, "approach_tdb")),
                Rows.instant(rs, "approach_utc"),
                rs.getString("t_sigma"),
                rs.getDouble("dist_au"),
                rs.getDouble("dist_km"),
                rs.getDouble("dist_ld"),
                Rows.decimal(rs, "dist_min_km"),
                Rows.decimal(rs, "dist_max_km"),
                Rows.decimal(rs, "v_rel_kms"),
                Rows.decimal(rs, "v_inf_kms"),
                Rows.decimal(rs, "h_mag"),
                Rows.decimal(rs, "diameter_km"),
                Rows.decimal(rs, "diameter_sigma_km"),
                Rows.decimal(rs, "diameter_min_km"),
                Rows.decimal(rs, "diameter_max_km"),
                rs.getBoolean("sentry"));
    }
}
