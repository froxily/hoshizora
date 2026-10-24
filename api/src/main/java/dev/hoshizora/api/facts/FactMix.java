package dev.hoshizora.api.facts;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;

final class FactMix {

    private FactMix() {}

    static List<FactRow> acrossModules(List<FactRow> bestFirst) {
        var perModule = new HashMap<String, Integer>();
        var rounds = new ArrayList<List<FactRow>>();
        for (var row : bestFirst) {
            int round = perModule.merge(row.module(), 1, Integer::sum) - 1;
            if (round == rounds.size()) {
                rounds.add(new ArrayList<>());
            }
            rounds.get(round).add(row);
        }
        return rounds.stream().flatMap(List::stream).toList();
    }
}
