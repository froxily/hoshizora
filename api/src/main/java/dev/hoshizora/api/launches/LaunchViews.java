package dev.hoshizora.api.launches;

import dev.hoshizora.api.common.Refs;
import dev.hoshizora.api.i18n.Lang;
import dev.hoshizora.api.i18n.Vocabulary;
import org.jspecify.annotations.Nullable;
import org.springframework.stereotype.Component;

@Component
public final class LaunchViews {

    private final Vocabulary vocabulary;
    private final Refs refs;

    LaunchViews(Vocabulary vocabulary, Refs refs) {
        this.vocabulary = vocabulary;
        this.refs = refs;
    }

    public LaunchSummary summary(LaunchRow row, Lang lang) {
        return new LaunchSummary(
                row.id(),
                row.name(),
                Lang.EN,
                row.net(),
                vocabulary.fromSource("net_precision", row.netPrecision(), lang),
                vocabulary.term("launch_status", row.outcome(), lang),
                row.launchDesignator(),
                row.provider() == null ? null : refs.organization(row.provider(), lang),
                vehicle(row.vehicle(), lang),
                pad(row.pad(), lang),
                mission(row.mission(), lang, false));
    }

    LaunchDetail detail(LaunchDetailRow detail, Lang lang) {
        var row = detail.launch();
        return new LaunchDetail(
                row.id(),
                row.name(),
                Lang.EN,
                row.net(),
                vocabulary.fromSource("net_precision", row.netPrecision(), lang),
                vocabulary.term("launch_status", row.outcome(), lang),
                row.launchDesignator(),
                row.provider() == null ? null : refs.organization(row.provider(), lang),
                vehicle(row.vehicle(), lang),
                pad(row.pad(), lang),
                mission(row.mission(), lang, true),
                detail.windowStart(),
                detail.windowEnd(),
                detail.failureReason(),
                detail.failureReason() == null ? null : Lang.EN,
                detail.programs().stream()
                        .map(program -> refs.program(program.slug(), program.name(), lang))
                        .toList(),
                detail.partners().stream()
                        .map(partner -> refs.organization(partner, lang))
                        .toList(),
                detail.objects().stream().map(object -> object(object, lang)).toList(),
                detail.objectsTotal(),
                detail.lineage());
    }

    private LaunchDetail.LaunchObject object(LaunchDetailRow.SpaceObject object, Lang lang) {
        return new LaunchDetail.LaunchObject(
                object.noradId(),
                object.objectId(),
                object.name(),
                vocabulary.term("object_type", object.objectType(), lang),
                vocabulary.term("orbit_state", object.orbitState(), lang),
                object.ownerCode(),
                object.decayDate());
    }

    private static LaunchSummary.@Nullable Vehicle vehicle(LaunchRow.@Nullable Vehicle vehicle, Lang lang) {
        if (vehicle == null) {
            return null;
        }
        var name = vehicle.name().in(lang);
        return new LaunchSummary.Vehicle(vehicle.id(), name.value(), name.lang(), vehicle.family(), vehicle.variant());
    }

    private LaunchSummary.@Nullable Pad pad(LaunchRow.@Nullable Pad pad, Lang lang) {
        if (pad == null) {
            return null;
        }
        return new LaunchSummary.Pad(
                pad.id(),
                pad.name(),
                Lang.EN,
                pad.location(),
                refs.country(pad.countryCode(), pad.countryEn(), pad.countryJa(), lang),
                pad.latitude(),
                pad.longitude());
    }

    private LaunchSummary.@Nullable Mission mission(
            LaunchRow.@Nullable Mission mission, Lang lang, boolean withDescription) {
        if (mission == null) {
            return null;
        }
        var name = mission.name().in(lang);
        var description = withDescription ? mission.description() : null;
        return new LaunchSummary.Mission(
                mission.id(),
                name.value(),
                name.lang(),
                vocabulary.fromSource("mission_type", mission.type(), lang),
                vocabulary.fromSource("orbit", mission.orbit(), mission.orbitName(), lang),
                description,
                description == null ? null : Lang.EN);
    }
}
