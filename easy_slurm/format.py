import re
from datetime import datetime
from typing import Any, Optional, Sequence


def format_with_config(
    template: str, config: dict[str, Any], _now: Optional[datetime] = None
) -> str:
    """Formats template using given config.

    The template syntax is very similar to Python string templates.
    One useful addition is that nested `config` keys can be accessed
    via "namespace" syntax.
    For instance,
    ```python
    "{nested.dict.key}"             ==> config["nested"]["dict"]["key"]
    "{hp.batch_size:06}"            ==> "000032"
    ```

    Additionally, some built-in keys have special formatting syntax.
    If these keys are present in `config`, they will be ignored.
    For instance,
    ```python
    "{date:%Y-%m-%d}"               ==> "2020-01-01"
    "{date:%Y-%m-%d %H:%M:%S.%3f}"  ==> "2020-01-01 00:00:03.141"
    ```

    See the examples below.

    Args:
        template: String to format.
        config: Key-value data to replace `"{key:format_spec}"` with.

    Returns:
        Formatted string.

    Examples:
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
    matches = list(re.finditer(r"\{[^\}]*\}", template))
    spans = [match.span() for match in matches]
    spans = [(0, 0)] + spans + [(len(template), len(template))]
    formatted_result = "".join(
        x
        for (l1, r1), (l2, _) in zip(spans[:-1], spans[1:])
        for x in [
            _format_term(template[l1:r1], config, now=_now),
            template[r1:l2],
        ]
    )
    return formatted_result


def dict_get(d: dict[str, Any], path_seq: Sequence[str]) -> Any:
    """Gets dictionary element of key path.

    Examples:
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
        >>> config = {"hp": {"batch_size": 32, "lr": 1e-2}}
        >>> dict_set(config, "hp.batch_size".split("."), 64)
        >>> config["hp"]["batch_size"]
        64
    """
    for key in path_seq[:-1]:
        d = d[key]
    d[path_seq[-1]] = value


def _format_term(term: str, config: dict[str, Any], now: datetime) -> str:
    """Formats term using given config.

    Examples:
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

    term = term[1:-1]  # trim surrounding {}

    key, *opt = term.split(":", maxsplit=1)

    if key == "date":
        fmt = opt[0] if len(opt) != 0 else "%Y-%m-%d_%H-%M-%S_%3f"
        return _strftime(fmt, now)

    fmt = "{}" if len(opt) == 0 else f"{{:{opt[0]}}}"
    return fmt.format(dict_get(config, key.split(".")))


def _strftime(fmt: str, dt: datetime) -> str:
    """Formats via strftime, but also supports width specifiers.

    See more information `here <so>`_.

    .. note:: `%%` specifier is not supported.

    .. _so: https://stackoverflow.com/a/71715115/365102

    Examples:
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
