package dev.hoshizora.api.launches;

import dev.hoshizora.api.common.OrganizationRow;
import dev.hoshizora.api.db.Rows;
import dev.hoshizora.api.i18n.Bilingual;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.UUID;

public final class LaunchRows {

    private LaunchRows() {}

    public static LaunchRow summary(ResultSet rs) throws SQLException {
        var providerKey = rs.getString("provider_key");
        var vehicleId = Rows.integer(rs, "vehicle_id");
        var padId = Rows.integer(rs, "pad_id");
        var missionId = Rows.integer(rs, "mission_id");
        return new LaunchRow(
                rs.getObject("launch_id", UUID.class),
                rs.getString("name"),
                Rows.instant(rs, "net"),
                rs.getString("net_precision"),
                rs.getString("outcome"),
                rs.getString("launch_designator"),
                Rows.whole(rs, "provider_org_id"),
                providerKey == null
                        ? null
                        : new OrganizationRow(
                                providerKey,
                                new Bilingual(rs.getString("provider_name_en"), rs.getString("provider_name_ja")),
                                rs.getString("provider_type")),
                vehicleId == null
                        ? null
                        : new LaunchRow.Vehicle(
                                vehicleId,
                                new Bilingual(rs.getString("vehicle_name"), rs.getString("vehicle_name_ja")),
                                rs.getString("vehicle_family"),
                                rs.getString("vehicle_variant")),
                padId == null
                        ? null
                        : new LaunchRow.Pad(
                                padId,
                                rs.getString("pad_name"),
                                rs.getString("pad_location"),
                                rs.getString("pad_country_code"),
                                rs.getString("pad_country_en"),
                                rs.getString("pad_country_ja"),
                                Rows.decimal(rs, "pad_latitude"),
                                Rows.decimal(rs, "pad_longitude")),
                missionId == null
                        ? null
                        : new LaunchRow.Mission(
                                missionId,
                                new Bilingual(rs.getString("mission_name"), rs.getString("mission_name_ja")),
                                rs.getString("mission_type"),
                                rs.getString("mission_orbit"),
                                rs.getString("mission_orbit_name"),
                                rs.getString("mission_description")));
    }
}
