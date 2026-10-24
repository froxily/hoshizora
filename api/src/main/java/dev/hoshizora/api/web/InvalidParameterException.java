package dev.hoshizora.api.web;

public final class InvalidParameterException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    private final String parameter;
    private final String messageKey;
    private final transient Object[] arguments;

    public InvalidParameterException(String parameter, String messageKey, Object... arguments) {
        super(parameter + ": " + messageKey);
        this.parameter = parameter;
        this.messageKey = messageKey;
        this.arguments = arguments.clone();
    }

    public String parameter() {
        return parameter;
    }

    public String messageKey() {
        return messageKey;
    }

    public Object[] arguments() {
        return arguments.clone();
    }
}
