package dev.hoshizora.api.spaceweather;

import dev.hoshizora.api.web.ApiValue;

public enum FlareClass implements ApiValue {
    A("A", 1e-8),
    B("B", 1e-7),
    C("C", 1e-6),
    M("M", 1e-5),
    X("X", 1e-4);

    private final String value;
    private final double minimumFluxWm2;

    FlareClass(String value, double minimumFluxWm2) {
        this.value = value;
        this.minimumFluxWm2 = minimumFluxWm2;
    }

    @Override
    public String value() {
        return value;
    }

    public double minimumFluxWm2() {
        return minimumFluxWm2;
    }
}
