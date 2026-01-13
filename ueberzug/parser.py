"""This module defines data parser
which can be used to exchange information between processes.
"""

import json
import abc
import shlex
import itertools
import enum
import re


class Parser:
    """Subclasses of this abstract class define
    how to input will be parsed.
    """

    @staticmethod
    @abc.abstractmethod
    def get_name():
        """Returns the constant name which is associated to this parser."""
        raise NotImplementedError()

    @abc.abstractmethod
    def parse(self, line):
        """Parses a line.

        Args:
            line (str): read line

        Returns:
            dict containing the key value pairs of the line
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def unparse(self, data):
        """Composes the data to a string
        whichs follows the syntax of the parser.

        Args:
            data (dict): data as key value pairs

        Returns:
            string
        """
        raise NotImplementedError()


class JsonParser(Parser):
    """Parses json input"""

    @staticmethod
    def get_name():
        return "json"

    def parse(self, line):
        try:
            data = json.loads(line)
            if not isinstance(data, dict):
                raise ValueError(
                    "Expected to parse an json object, got " + line
                )
            return data
        except json.JSONDecodeError as error:
            raise ValueError(error)

    def unparse(self, data):
        return json.dumps(data)


class SimpleParser(Parser):
    """Parses key value pairs separated by a tab.
    Does not support escaping spaces.
    """

    SEPARATOR = "\t"

    @staticmethod
    def get_name():
        return "simple"

    def parse(self, line):
        components = line.split(SimpleParser.SEPARATOR)

        if len(components) % 2 != 0:
            raise ValueError(
                "Expected key value pairs, "
                + "but at least one key has no value: "
                + line
            )

        return {
            key: value
            for key, value in itertools.zip_longest(
                components[::2], components[1::2]
            )
        }

    def unparse(self, data):
        return SimpleParser.SEPARATOR.join(
            str(key) + SimpleParser.SEPARATOR + str(value.replace("\n", ""))
            for key, value in data.items()
        )


class BashParser(Parser):
    """Parses input generated
    by dumping associative arrays with `declare -p`.
    """

    @staticmethod
    def get_name():
        return "bash"

    def parse(self, line):
        def multi_sub(s, patterns):
            def repl(match):
                for i, group in enumerate(match.groups()):
                    if group:
                        _, replacement = patterns[i]
                        return replacement(group) if callable(replacement) else replacement
                return ""
            patterns = list(patterns.items())
            return re.sub("|".join(f"({p})" for p, _ in patterns), repl, s)

        def unquote(s):
            # Taken from https://www.gnu.org/software/bash/manual/html_node/Quoting.html
            if s[0] == "'" and s[-1] == "'":
                return s[1:-1]
            elif s[0] == '"' and s[-1] == '"':
                return multi_sub(s[1:-1], {
                    r"\\\\": "\\",
                    r"\\\"": '"',
                    r"\\\$": "$",
                    r"\\`": "`",
                })
            elif s.startswith("$'") and s.endswith("'"):
                return multi_sub(s[2:-1], {
                    r"\\a": "\a",
                    r"\\b": "\b",
                    r"\\e": "\x1B",
                    r"\\E": "\x1B",
                    r"\\f": "\f",
                    r"\\n": "\n",
                    r"\\r": "\r",
                    r"\\t": "\t",
                    r"\\v": "\v",
                    r"\\\\": "\\",
                    r"\\'": "'",
                    r'\\"': '"',
                    r"\\\?": "?",
                    r"\\[0-9]{1,3}": lambda m: chr(int(m[1:], base=8)),
                    r"\\x[0-9A-Fa-f]{1,2}": lambda m: chr(int(m[2:], base=16)),
                    r"\\u[0-9A-Fa-f]{1,4}": lambda m: chr(int(m[2:], base=16)),
                    r"\\U[0-9A-Fa-f]{1,8}": lambda m: chr(int(m[2:], base=16)),
                    # Taken from chartypes.h in bash
                    # #define TOCTRL(x)	((x) == '?' ? 0x7f : (TOUPPER(x) & 0x1f))
                    r"\\c[\x01-\x7F]": lambda m: "\x7F" if m[2:] == "?" else chr(ord(m[2:].upper()) & 0x1F),
                })
            return s

        def expect(token, expectation):
            if isinstance(expectation, str) and token != expectation \
                    or token not in expectation:
                raise ValueError(
                    "Expected input to be formatted like "
                    "the output of the `declare -p` command from bash. "
                    "Got: " + line
                )

        lexer = shlex.shlex(line)
        expect(lexer.get_token(), ["declare", "typeset"])
        expect(lexer.get_token(), "-")
        expect(lexer.get_token(), "A")
        lexer.get_token()
        expect(lexer.get_token(), "=")
        expect(lexer.get_token(), "(")

        data = {}
        while (token := lexer.get_token()) not in [")", lexer.eof]:
            expect(token, "[")
            token = lexer.get_token()
            if token == "$":
                token += lexer.get_token()
            key = unquote(token)
            expect(lexer.get_token(), "]")
            expect(lexer.get_token(), "=")
            token = lexer.get_token()
            if token == "$":
                token += lexer.get_token()
            data[key] = unquote(token)
        expect(token, ")")

        return data

    def unparse(self, data):
        return " ".join(
            "[" + str(key) + "]=" + shlex.quote(value)
            for key, value in data.items()
        )


@enum.unique
class ParserOption(str, enum.Enum):
    JSON = JsonParser
    SIMPLE = SimpleParser
    BASH = BashParser

    def __new__(cls, parser_class):
        inst = str.__new__(cls)
        inst._value_ = parser_class.get_name()
        inst.parser_class = parser_class
        return inst
