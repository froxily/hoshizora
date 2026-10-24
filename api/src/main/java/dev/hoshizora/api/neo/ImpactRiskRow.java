package dev.hoshizora.api.neo;

import dev.hoshizora.api.db.Rows;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.time.LocalDate;
import org.jspecify.annotations.Nullable;

record ImpactRiskRow(
        String designation,
        @Nullable String fullname,
        @Nullable Double impactProbability,
        @Nullable Double palermoCumulative,
        @Nullable Double palermoMax,
        @Nullable Integer torinoMax,
        @Nullable Integer potentialImpacts,
        @Nullable Integer impactYearFirst,
        @Nullable Integer impactYearLast,
        @Nullable LocalDate lastObserved,
        @Nullable Double diameterKm,
        @Nullable Double hMag,
        @Nullable Double vInfKms,
        @Nullable Instant removedAt,
        @Nullable Double diameterMinKm,
        @Nullable Double diameterMaxKm) {

    static ImpactRiskRow of(ResultSet rs) throws SQLException {
        return new ImpactRiskRow(
                rs.getString("designation"),
                rs.getString("fullname"),
                Rows.decimal(rs, "impact_probability"),
                Rows.decimal(rs, "palermo_cumulative"),
                Rows.decimal(rs, "palermo_max"),
                Rows.integer(rs, "torino_max"),
                Rows.integer(rs, "potential_impacts"),
                Rows.integer(rs, "impact_year_first"),
                Rows.integer(rs, "impact_year_last"),
                Rows.date(rs, "last_observed"),
                Rows.decimal(rs, "diameter_km"),
                Rows.decimal(rs, "h_mag"),
                Rows.decimal(rs, "v_inf_kms"),
                Rows.instant(rs, "removed_at"),
                Rows.decimal(rs, "diameter_min_km"),
                Rows.decimal(rs, "diameter_max_km"));
    }
}
