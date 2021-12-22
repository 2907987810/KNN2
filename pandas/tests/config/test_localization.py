import codecs
import locale
import os

import pytest

from pandas._config.localization import (
    can_set_locale,
    get_locales,
    set_locale,
)

from pandas.compat import is_platform_windows

import pandas as pd
import pandas._testing as tm

_all_locales = get_locales() or []
_current_locale = locale.getlocale()

# Don't run any of these tests if we are on Windows or have no locales.
pytestmark = pytest.mark.skipif(
    is_platform_windows() or not _all_locales, reason="Need non-Windows and locales"
)

_skip_if_only_one_locale = pytest.mark.skipif(
    len(_all_locales) <= 1, reason="Need multiple locales for meaningful test"
)


def test_can_set_locale_valid_set():
    # Can set the default locale.
    assert can_set_locale("")


def test_can_set_locale_invalid_set():
    # Cannot set an invalid locale.
    assert not can_set_locale("non-existent_locale")


def test_can_set_locale_invalid_get(monkeypatch):
    # see GH#22129
    # In some cases, an invalid locale can be set,
    #  but a subsequent getlocale() raises a ValueError.

    def mock_get_locale():
        raise ValueError()

    with monkeypatch.context() as m:
        m.setattr(locale, "getlocale", mock_get_locale)
        assert not can_set_locale("")


def test_get_locales_at_least_one():
    # see GH#9744
    assert len(_all_locales) > 0


@_skip_if_only_one_locale
def test_get_locales_prefix():
    first_locale = _all_locales[0]
    assert len(get_locales(prefix=first_locale[:2])) > 0


@_skip_if_only_one_locale
@pytest.mark.parametrize("test_local", tm.TESTING_LOCALES)
def test_set_locale(test_local):
    lang, enc = test_local.split(".")
    enc = codecs.lookup(enc).name
    new_locale = lang, enc

    if not can_set_locale(new_locale):
        msg = "unsupported locale setting"

        with pytest.raises(locale.Error, match=msg):
            with set_locale(new_locale):
                pass
    else:
        with set_locale(new_locale) as normalized_locale:
            new_lang, new_enc = normalized_locale.split(".")
            new_enc = codecs.lookup(enc).name

            normalized_locale = new_lang, new_enc
            assert normalized_locale == new_locale

    # Once we exit the "with" statement, locale should be back to what it was.
    current_locale = locale.getlocale()
    assert current_locale == _current_locale


def test_encoding_detected():
    system_locale = os.environ.get("LC_ALL")
    system_encoding = system_locale.split(".")[-1] if system_locale else "utf-8"

    assert (
        codecs.lookup(pd.options.display.encoding).name
        == codecs.lookup(system_encoding).name
    )
