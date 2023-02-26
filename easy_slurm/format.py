import re
from datetime import datetime
from typing import Any, Optional, Sequence

__all__ = [
    "format_with_config",
]


def format_with_config(
    template: str,
    config: dict[str, Any],
    silent: bool = False,
    _now: Optional[datetime] = None,
) -> str:
    """Formats template using given config.

    The template syntax is very similar to Python string templates.
    One useful addition is that nested ``config`` keys can be accessed
    via "namespace" syntax.
    For instance,

    .. code-block:: python

        "{nested.dict.key}"             ==> config["nested"]["dict"]["key"]
        "{hp.batch_size:06}"            ==> "000032"

    Additionally, some built-in keys have special formatting syntax.
    If these keys are present in ``config``, they will be ignored.
    For instance,

    .. code-block:: python

        "{date:%Y-%m-%d}"               ==> "2020-01-01"
        "{date:%Y-%m-%d %H:%M:%S.%3f}"  ==> "2020-01-01 00:00:03.141"

    See the examples below.

    Args:
        template: String to format.
        config: Key-value data to replace ``"{key:format_spec}"`` with.
        silent: Silently pass-through ``"{key:format_spec}"`` if key not
            in ``config``.

    Returns:
        Formatted string.

    Examples:

    .. code-block:: python

        >>> from datetime import datetime
        >>> date_string = "2020-01-01 00:00:03.141592"
        >>> now = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S.%f")
        >>> config = {"hp": {"batch_size": 32, "lr": 1e-2}}
        >>> fmt = "{date:%Y-%m-%d}_bs={hp.batch_size:04},lr={hp.lr:.1e}"
        >>> format_with_config(fmt, config, _now=now)
        '2020-01-01_bs=0032,lr=1.0e-02'
        >>> fmt = "{date:%Y-%m-%d_%H-%M-%S_%3f}_bs={hp.batch_size}"
        >>> format_with_config(fmt, config, _now=now)
        '2020-01-01_00-00-03_141_bs=32'
    """
    if _now is None:
        _now = datetime.now()

    template = encode_pair("{{", "}}", 2, template)
    matches = list(re.finditer(r"\{[^\}]*\}", template))
    spans = [match.span() for match in matches]
    spans = [(0, 0)] + spans + [(len(template), len(template))]
    formatted_result = "".join(
        x
        for (l1, r1), (l2, _) in zip(spans[:-1], spans[1:])
        for x in [
            _format_term(template[l1:r1], config, now=_now, silent=silent),
            template[r1:l2],
        ]
    )
    formatted_result = decode_pair("{", "}", 2, formatted_result)
    return formatted_result


def dict_get(d: dict[str, Any], path_seq: Sequence[str]) -> Any:
    """Gets dictionary element of key path.

    Examples:

    .. code-block:: python

        >>> config = {"hp": {"batch_size": 32, "lr": 1e-2}}
        >>> dict_get(config, "hp.batch_size".split("."))
        32
    """
    for key in path_seq:
        d = d[key]
    return d


def dict_set(d: dict[str, Any], path_seq: Sequence[str], value: Any):
    """Sets dictionary element of key path with given value.

    Examples:

    .. code-block:: python

        >>> config = {"hp": {"batch_size": 32, "lr": 1e-2}}
        >>> dict_set(config, "hp.batch_size".split("."), 64)
        >>> config["hp"]["batch_size"]
        64
    """
    for key in path_seq[:-1]:
        d = d[key]
    d[path_seq[-1]] = value


def encode_pair(left: str, right: str, rep: int, s: str) -> str:
    """Encodes a left/right pair using temporary characters."""
    return (
        s.replace("", "")
        .replace(left, "\ufffe" * rep)
        .replace(right, "\uffff" * rep)
    )


def decode_pair(left: str, right: str, rep: int, s: str) -> str:
    """Decodes a left/right pair using temporary characters."""
    return (
        s.replace("", "")
        .replace("\ufffe" * rep, left)
        .replace("\uffff" * rep, right)
    )


def _format_term(
    term: str, config: dict[str, Any], now: datetime, silent: bool = False
) -> str:
    """Formats term using given config.

    Examples:

    .. code-block:: python

        >>> from datetime import datetime
        >>> date_string = "2020-01-01 00:00:03.141592"
        >>> now = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S.%f")
        >>> config = {"hp": {"batch_size": 32, "lr": 1e-2}}
        >>> _format_term("{hp.batch_size:04}", config)
        '0032'
        >>> _format_term("{hp.lr:.1e}", config)
        '1.0e-02'
        >>> _format_term("{date:%Y-%m-%d_%H-%M-%S_%3f}", config, now=now)
        '2020-01-01_00-00-03_141'
    """
    if term == "":
        return ""

    key, *opt = term[1:-1].split(":", maxsplit=1)

    if key == "date":
        fmt = opt[0] if len(opt) != 0 else "%Y-%m-%d_%H-%M-%S_%3f"
        return _strftime(fmt, now)

    fmt = "{}" if len(opt) == 0 else f"{{:{opt[0]}}}"

    try:
        value = dict_get(config, key.split("."))
    except KeyError as e:
        if silent:
            return term
        raise e

    return fmt.format(value)


def _strftime(fmt: str, dt: datetime) -> str:
    """Formats via strftime, but also supports width specifiers.

    See more information `here <so>`_.

    .. note:: `%%` specifier is not supported.

    .. _so: https://stackoverflow.com/a/71715115/365102

    Examples:

    .. code-block:: python

        >>> from datetime import datetime
        >>> date_string = "2020-01-01 00:00:03.141592"
        >>> dt = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S.%f")
        >>> _strftime("%Y-%m-%d %H:%M:%S.%3f", dt)
        '2020-01-01 00:00:03.141'
    """
    tokens = fmt.split("%")
    tokens[1:] = [_strftime_format_token(dt, x) for x in tokens[1:]]
    return "".join(tokens)


def _strftime_format_token(dt: datetime, token: str) -> str:
    if len(token) == 0:
        return ""
    if token[0].isnumeric():
        width = int(token[0])
        s = dt.strftime(f"%{token[1]}")[:width]
        return f"{s}{token[2:]}"
    return dt.strftime(f"%{token}")
