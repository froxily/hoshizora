package dev.hoshizora.api.spaceweather;

import dev.hoshizora.api.db.Rows;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.Objects;
import org.jspecify.annotations.Nullable;

final class SpaceWeatherRows {

    private SpaceWeatherRows() {}

    record KpRow(Instant observedAt, double kp, int gScale) {}

    record FlareRow(
            String id,
            @Nullable Instant beginAt,
            @Nullable Instant peakAt,
            @Nullable Instant endAt,
            @Nullable String xrayClass,
            @Nullable Double peakFluxWm2,
            @Nullable Integer rScale,
            @Nullable Integer satellite) {}

    record NowRow(
            @Nullable KpRow kp,
            SolarWind.@Nullable Point wind,
            @Nullable FlareRow flare,
            long flaresLastDay) {}

    static KpRow kp(ResultSet rs) throws SQLException {
        return new KpRow(
                Objects.requireNonNull(Rows.instant(rs, "observed_at")), rs.getDouble("kp"), rs.getInt("g_scale"));
    }

    static FlareRow flare(ResultSet rs, String prefix) throws SQLException {
        return new FlareRow(
                rs.getString(prefix + "id"),
                Rows.instant(rs, prefix + "begin_at"),
                Rows.instant(rs, prefix + "peak_at"),
                Rows.instant(rs, prefix + "end_at"),
                rs.getString(prefix + "xray_class"),
                Rows.decimal(rs, prefix + "peak_flux_wm2"),
                Rows.integer(rs, prefix + "r_scale"),
                Rows.integer(rs, prefix + "satellite"));
    }

    static SolarWind.Point wind(ResultSet rs, String timeColumn) throws SQLException {
        return new SolarWind.Point(
                Objects.requireNonNull(Rows.instant(rs, timeColumn)),
                Rows.decimal(rs, "speed_kms"),
                Rows.decimal(rs, "density_cm3"),
                Rows.decimal(rs, "temperature_k"),
                Rows.decimal(rs, "bt_nt"),
                Rows.decimal(rs, "bz_gsm_nt"),
                Rows.decimal(rs, "speed_kms_max"),
                Rows.decimal(rs, "bz_gsm_nt_min"),
                Rows.integer(rs, "samples"));
    }

    static NowRow now(ResultSet rs) throws SQLException {
        var kpObservedAt = Rows.instant(rs, "kp_observed_at");
        var windObservedAt = Rows.instant(rs, "wind_observed_at");
        return new NowRow(
                kpObservedAt == null ? null : new KpRow(kpObservedAt, rs.getDouble("kp"), rs.getInt("g_scale")),
                windObservedAt == null ? null : wind(rs, "wind_observed_at"),
                rs.getString("flare_id") == null ? null : flare(rs, "flare_"),
                rs.getLong("flares_last_day"));
    }
}
