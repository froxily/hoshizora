package dev.hoshizora.api.agencies;

import dev.hoshizora.api.db.Rows;
import dev.hoshizora.api.i18n.Bilingual;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import org.jspecify.annotations.Nullable;

record AgencyRow(
        long id,
        String key,
        Bilingual name,
        @Nullable String nameJaSource,
        @Nullable String abbrev,
        @Nullable String type,
        @Nullable Integer foundingYear,
        @Nullable Long parentId,
        @Nullable Totals launches,
        List<Named> countries,
        List<Named> programs) {

    record Totals(
            long attempts,
            long successes,
            long failures,
            long partialFailures,
            long scheduled,
            @Nullable Instant firstLaunchAt,
            @Nullable Instant lastLaunchAt) {}

    record Named(String code, Bilingual name) {}

    static AgencyRow of(ResultSet rs) throws SQLException {
        var attempts = Rows.whole(rs, "attempts");
        return new AgencyRow(
                rs.getLong("id"),
                rs.getString("key"),
                new Bilingual(rs.getString("name_en"), rs.getString("name_ja")),
                rs.getString("name_ja_source"),
                rs.getString("abbrev"),
                rs.getString("type"),
                Rows.integer(rs, "founding_year"),
                Rows.whole(rs, "parent_id"),
                attempts == null
                        ? null
                        : new Totals(
                                attempts,
                                rs.getLong("successes"),
                                rs.getLong("failures"),
                                rs.getLong("partial_failures"),
                                rs.getLong("scheduled"),
                                Rows.instant(rs, "first_launch_at"),
                                Rows.instant(rs, "last_launch_at")),
                named(rs, "country_codes", "country_names"),
                named(rs, "program_slugs", "program_names"));
    }

    private static List<Named> named(ResultSet rs, String codes, String names) throws SQLException {
        var keys = Rows.strings(rs, codes);
        var en = Rows.strings(rs, names + "_en");
        var ja = Rows.strings(rs, names + "_ja");
        var result = new ArrayList<Named>(keys.size());
        for (var i = 0; i < keys.size(); i++) {
            result.add(new Named(keys.get(i), new Bilingual(en.get(i), ja.get(i))));
        }
        return List.copyOf(result);
    }
}
