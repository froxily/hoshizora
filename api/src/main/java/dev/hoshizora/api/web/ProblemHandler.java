package dev.hoshizora.api.web;

import java.util.List;
import java.util.Map;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.TypeMismatchException;
import org.springframework.context.MessageSource;
import org.springframework.context.MessageSourceResolvable;
import org.springframework.context.i18n.LocaleContextHolder;
import org.springframework.core.MethodParameter;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.FieldError;
import org.springframework.web.ErrorResponse;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.context.request.WebRequest;
import org.springframework.web.method.annotation.HandlerMethodValidationException;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;

@RestControllerAdvice
class ProblemHandler extends ResponseEntityExceptionHandler {

    private static final Logger LOG = LoggerFactory.getLogger(ProblemHandler.class);
    private static final Map<Integer, String> CODES = Map.of(
            400, "invalid_parameter",
            404, "not_found",
            405, "method_not_allowed",
            406, "not_acceptable",
            500, "internal_error");

    private final MessageSource messages;

    ProblemHandler(MessageSource messages) {
        this.messages = messages;
        setMessageSource(messages);
    }

    @Override
    protected @Nullable ResponseEntity<Object> handleHandlerMethodValidationException(
            HandlerMethodValidationException ex, HttpHeaders headers, HttpStatusCode status, WebRequest request) {
        var errors = ex.getParameterValidationResults().stream()
                .flatMap(result -> result.getResolvableErrors().stream()
                        .map(error -> invalid(nameOf(result.getMethodParameter(), error), error)))
                .toList();
        return withErrors(super.handleHandlerMethodValidationException(ex, headers, status, request), errors);
    }

    @Override
    protected @Nullable ResponseEntity<Object> handleMethodArgumentNotValid(
            MethodArgumentNotValidException ex, HttpHeaders headers, HttpStatusCode status, WebRequest request) {
        var errors = ex.getFieldErrors().stream()
                .map(error -> invalid(error.getField(), error))
                .toList();
        return withErrors(super.handleMethodArgumentNotValid(ex, headers, status, request), errors);
    }

    @Override
    protected @Nullable ResponseEntity<Object> handleTypeMismatch(
            TypeMismatchException ex, HttpHeaders headers, HttpStatusCode status, WebRequest request) {
        var name = ex.getPropertyName() == null ? "" : ex.getPropertyName();
        var error = new InvalidParameter(
                name, messages.getMessage("validation.invalid_value", null, LocaleContextHolder.getLocale()));
        return withErrors(super.handleTypeMismatch(ex, headers, status, request), List.of(error));
    }

    @ExceptionHandler(InvalidParameterException.class)
    ResponseEntity<Object> handleInvalidParameter(InvalidParameterException ex, WebRequest request) {
        var locale = LocaleContextHolder.getLocale();
        var body = ErrorResponse.builder(ex, HttpStatus.BAD_REQUEST, "Invalid parameters")
                .titleMessageCode("problemDetail.title.invalid_parameter")
                .detailMessageCode("problemDetail.invalid_parameter")
                .build()
                .updateAndGetBody(messages, locale);
        body.setProperty(
                "errors",
                List.of(new InvalidParameter(
                        ex.parameter(), messages.getMessage(ex.messageKey(), ex.arguments(), locale))));
        return createResponseEntity(body, new HttpHeaders(), HttpStatus.BAD_REQUEST, request);
    }

    @ExceptionHandler(Exception.class)
    ResponseEntity<Object> handleUnexpected(Exception ex, WebRequest request) {
        LOG.error("Unhandled API error", ex);
        var body = ErrorResponse.builder(ex, HttpStatus.INTERNAL_SERVER_ERROR, "Internal error")
                .titleMessageCode("problemDetail.title.internal")
                .detailMessageCode("problemDetail.internal")
                .build()
                .updateAndGetBody(messages, LocaleContextHolder.getLocale());
        return createResponseEntity(body, new HttpHeaders(), HttpStatus.INTERNAL_SERVER_ERROR, request);
    }

    @Override
    protected ResponseEntity<Object> createResponseEntity(
            @Nullable Object body, HttpHeaders headers, HttpStatusCode statusCode, WebRequest request) {
        if (body instanceof ProblemDetail problem) {
            problem.setProperty("code", CODES.getOrDefault(statusCode.value(), "error"));
        }
        return super.createResponseEntity(body, headers, statusCode, request);
    }

    private InvalidParameter invalid(String name, MessageSourceResolvable error) {
        return new InvalidParameter(name, messages.getMessage(error, LocaleContextHolder.getLocale()));
    }

    private static String nameOf(MethodParameter parameter, MessageSourceResolvable error) {
        if (error instanceof FieldError field) {
            return field.getField();
        }
        var requestParam = parameter.getParameterAnnotation(RequestParam.class);
        if (requestParam != null) {
            var declared = requestParam.name().isEmpty() ? requestParam.value() : requestParam.name();
            if (!declared.isEmpty()) {
                return declared;
            }
        }
        var name = parameter.getParameterName();
        return name == null ? "" : name;
    }

    private static @Nullable ResponseEntity<Object> withErrors(
            @Nullable ResponseEntity<Object> response, List<InvalidParameter> errors) {
        if (response != null && response.getBody() instanceof ProblemDetail problem) {
            problem.setProperty("errors", errors);
        }
        return response;
    }
}
