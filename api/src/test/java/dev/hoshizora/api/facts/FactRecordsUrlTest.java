package dev.hoshizora.api.facts;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

class FactRecordsUrlTest {

    @ParameterizedTest
    @CsvSource(
            nullValues = "none",
            value = {
                "mart.organization_launch_summary, jaxa, /api/v1/agencies/jaxa",
                "core.space_weather_event, xray_flare|2026-10-16T06:22:00Z, /api/v1/space-weather/flares",
                "core.space_weather_event, alert|5435, none",
                "mart.kp_daily, 2026-10-15, /api/v1/space-weather/kp",
                "mart.solar_wind_hourly, 2026-10-18 05:00:00+00, /api/v1/space-weather/solar-wind",
                "mart.launch_pad_activity, 40, /api/v1/stats/launches/pads",
                "mart.objects_in_orbit_by_owner, earth_orbit, /api/v1/stats/orbits/countries",
                "mart.objects_in_orbit_by_country, JP|payload|earth_orbit, /api/v1/stats/orbits/countries",
                "core.launcher, 101, /api/v1/stats/launches/boosters",
                "core.landing, 1710, /api/v1/stats/launches/boosters",
                "mart.reusability_yearly, all|all|2025,"
                        + " /api/v1/stats/launches/reusability?group_by=all&key=all&from_year=2025&to_year=2025",
                "core.exoplanet, Proxima Cen b, /api/v1/exoplanets/Proxima%20Cen%20b",
                "mart.exoplanet_discoveries_yearly, 2016|Transit,"
                        + " /api/v1/stats/exoplanets/discoveries?from_year=2016&to_year=2016",
                "core.space_object, 25544, none",
            })
    void linksEachSourceToTheRecordsBehindIt(String entity, String key, String expected) {
        assertThat(FactController.recordsUrl(new FactRow.SourceRef(entity, key)))
                .isEqualTo(expected);
    }
}
