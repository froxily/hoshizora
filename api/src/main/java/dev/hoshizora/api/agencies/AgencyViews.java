package dev.hoshizora.api.agencies;

import dev.hoshizora.api.common.CountryRef;
import dev.hoshizora.api.common.ProgramRef;
import dev.hoshizora.api.common.Refs;
import dev.hoshizora.api.i18n.Lang;
import dev.hoshizora.api.i18n.Term;
import dev.hoshizora.api.i18n.Vocabulary;
import dev.hoshizora.api.launches.LaunchViews;
import java.util.List;
import org.jspecify.annotations.Nullable;
import org.springframework.stereotype.Component;

@Component
class AgencyViews {

    private final Vocabulary vocabulary;
    private final Refs refs;
    private final LaunchViews launches;

    AgencyViews(Vocabulary vocabulary, Refs refs, LaunchViews launches) {
        this.vocabulary = vocabulary;
        this.refs = refs;
        this.launches = launches;
    }

    AgencySummary summary(AgencyRow row, Lang lang) {
        var name = row.name().in(lang);
        return new AgencySummary(
                row.key(),
                name.value(),
                name.lang(),
                row.abbrev(),
                type(row, lang),
                countries(row, lang),
                programs(row, lang),
                row.foundingYear(),
                row.launches() == null ? null : LaunchStats.of(row.launches()));
    }

    AgencyDetail detail(AgencyDetailRow detail, Lang lang) {
        var row = detail.profile();
        var name = row.name().in(lang);
        var objects = detail.objects();
        return new AgencyDetail(
                row.key(),
                name.value(),
                name.lang(),
                row.name().ja() == null ? null : row.nameJaSource(),
                row.abbrev(),
                type(row, lang),
                countries(row, lang),
                programs(row, lang),
                row.foundingYear(),
                row.launches() == null ? null : LaunchStats.of(row.launches()),
                reliability(detail.reliability()),
                detail.parent() == null ? null : refs.organization(detail.parent(), lang),
                detail.members().stream()
                        .map(member -> refs.organization(member, lang))
                        .toList(),
                detail.vehicles().stream()
                        .map(vehicle -> {
                            var vehicleName = vehicle.name().in(lang);
                            return new AgencyDetail.VehicleUsage(
                                    vehicle.vehicleId(),
                                    vehicleName.value(),
                                    vehicleName.lang(),
                                    vehicle.family(),
                                    vehicle.attempts(),
                                    vehicle.successes());
                        })
                        .toList(),
                detail.recentLaunches().stream()
                        .map(launch -> launches.summary(launch, lang))
                        .toList(),
                detail.nextLaunch() == null ? null : launches.summary(detail.nextLaunch(), lang),
                detail.partnerMissions(),
                objects == null
                        ? null
                        : new AgencyDetail.CataloguedObjects(
                                objects.ownerCodes(),
                                objects.inEarthOrbit(),
                                objects.payloadsInEarthOrbit(),
                                objects.beyondEarth(),
                                objects.decayed()),
                detail.lineage());
    }

    private @Nullable Term type(AgencyRow row, Lang lang) {
        return row.type() == null ? null : vocabulary.term("organization_type", row.type(), lang);
    }

    private static List<CountryRef> countries(AgencyRow row, Lang lang) {
        return row.countries().stream()
                .map(country ->
                        new CountryRef(country.code(), country.name().in(lang).value()))
                .toList();
    }

    private List<ProgramRef> programs(AgencyRow row, Lang lang) {
        return row.programs().stream()
                .map(program -> refs.program(program.code(), program.name(), lang))
                .toList();
    }

    private static AgencyDetail.@Nullable Reliability reliability(AgencyDetailRow.@Nullable Reliability row) {
        if (row == null) {
            return null;
        }
        return new AgencyDetail.Reliability(
                row.recentAttempts(),
                row.recentSuccesses(),
                row.recentAttempts() == 0 ? null : (double) row.recentSuccesses() / row.recentAttempts(),
                row.currentStreak(),
                row.longestStreak());
    }
}
