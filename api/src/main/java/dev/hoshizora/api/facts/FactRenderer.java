package dev.hoshizora.api.facts;

import dev.hoshizora.api.i18n.Lang;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.text.NumberFormat;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.FormatStyle;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.jspecify.annotations.Nullable;
import org.springframework.stereotype.Component;

@Component
final class FactRenderer {

    private static final Pattern ARGUMENT = Pattern.compile(
            "\\{\\s*([a-z][a-z0-9_]*)\\s*(?:,\\s*(number|date)\\s*(?:,\\s*(integer|percent|compact)\\s*)?)?}");
    private static final int MAX_FRACTION_DIGITS = 6;

    String render(String template, Map<String, Object> params, Lang lang) {
        var matcher = ARGUMENT.matcher(template);
        var text = new StringBuilder();
        while (matcher.find()) {
            matcher.appendReplacement(text, Matcher.quoteReplacement(argument(matcher, params, lang)));
        }
        matcher.appendTail(text);
        return text.toString();
    }

    private static String argument(Matcher matcher, Map<String, Object> params, Lang lang) {
        var name = matcher.group(1);
        var value = params.get(name);
        if (value == null) {
            throw new FactRenderingException("missing param " + name);
        }
        if ("date".equals(matcher.group(2))) {
            return LocalDate.parse(value.toString())
                    .format(DateTimeFormatter.ofLocalizedDate(FormatStyle.LONG).withLocale(lang.locale()));
        }
        if (value instanceof Number number) {
            return number(new BigDecimal(number.toString()), matcher.group(3), lang);
        }
        if ("number".equals(matcher.group(2))) {
            throw new FactRenderingException("param " + name + " is not a number");
        }
        return text(value, lang);
    }

    private static String number(BigDecimal value, @Nullable String style, Lang lang) {
        var locale = lang.locale();
        var format = switch (style == null ? "" : style) {
            case "integer" -> NumberFormat.getIntegerInstance(locale);
            case "percent" -> fractions(NumberFormat.getPercentInstance(locale), Math.max(0, value.scale() - 2));
            case "compact" -> fractions(NumberFormat.getCompactNumberInstance(locale, NumberFormat.Style.SHORT), 1);
            default -> fractions(NumberFormat.getNumberInstance(locale), Math.max(0, value.scale()));
        };
        format.setRoundingMode(RoundingMode.HALF_UP);
        return "compact".equals(style) ? format.format(value.doubleValue()) : format.format(value);
    }

    private static NumberFormat fractions(NumberFormat format, int digits) {
        format.setMaximumFractionDigits(Math.min(digits, MAX_FRACTION_DIGITS));
        return format;
    }

    private static String text(Object value, Lang lang) {
        if (value instanceof Map<?, ?> localized) {
            var preferred = localized.get(lang.value());
            var fallback = localized.get(Lang.EN.value());
            var chosen = preferred == null ? fallback : preferred;
            if (chosen == null) {
                throw new FactRenderingException("localized param has no en value");
            }
            return chosen.toString();
        }
        return value.toString();
    }

    static final class FactRenderingException extends RuntimeException {

        private static final long serialVersionUID = 1L;

        FactRenderingException(String message) {
            super(message);
        }
    }
}
