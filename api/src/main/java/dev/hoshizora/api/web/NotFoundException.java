package dev.hoshizora.api.web;

import org.springframework.context.support.DefaultMessageSourceResolvable;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;

public final class NotFoundException extends ErrorResponseException {

    private static final long serialVersionUID = 1L;

    public NotFoundException(String resource, String id) {
        super(HttpStatus.NOT_FOUND, ProblemDetail.forStatus(HttpStatus.NOT_FOUND), null, null, new Object[] {
            new DefaultMessageSourceResolvable("resource." + resource), id
        });
    }
}
