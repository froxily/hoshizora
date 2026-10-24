package dev.hoshizora.api.i18n;

import java.util.Locale;
import java.util.regex.Pattern;
import org.jspecify.annotations.Nullable;
import org.springframework.context.MessageSource;
import org.springframework.stereotype.Component;

@Component
public final class Vocabulary {

    private static final Pattern NON_ALPHANUMERIC = Pattern.compile("[^a-z0-9]+");

    private final MessageSource messages;

    Vocabulary(MessageSource messages) {
        this.messages = messages;
    }

    public Term term(String kind, String code, Lang lang) {
        return new Term(code, messages.getMessage(key(kind, code), null, lang.locale()), lang);
    }

    public @Nullable Term fromSource(String kind, @Nullable String sourceLabel, Lang lang) {
        return fromSource(kind, sourceLabel, sourceLabel, lang);
    }

    public @Nullable Term fromSource(
            String kind, @Nullable String sourceCode, @Nullable String sourceLabel, Lang lang) {
        if (sourceCode == null || sourceCode.isBlank()) {
            return null;
        }
        var code = codeOf(sourceCode);
        var label = messages.getMessage(key(kind, code), null, null, lang.locale());
        if (label != null) {
            return new Term(code, label, lang);
        }
        return new Term(code, sourceLabel == null || sourceLabel.isBlank() ? sourceCode : sourceLabel, Lang.EN);
    }

    public String message(String key, Lang lang, Object... args) {
        return messages.getMessage(key, args, lang.locale());
    }

    static String codeOf(String sourceLabel) {
        var code =
                NON_ALPHANUMERIC.matcher(sourceLabel.toLowerCase(Locale.ROOT)).replaceAll("_");
        return code.replaceAll("^_+|_+$", "");
    }

    private static String key(String kind, String code) {
        return "vocab." + kind + "." + code;
    }
}
