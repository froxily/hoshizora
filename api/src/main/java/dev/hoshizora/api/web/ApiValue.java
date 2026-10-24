package dev.hoshizora.api.web;

import com.fasterxml.jackson.annotation.JsonValue;

public interface ApiValue {

    @JsonValue
    String value();
}
